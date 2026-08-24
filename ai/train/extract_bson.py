# -*- coding: utf-8 -*-
r"""LifeSnaps 원본 BSON(9.7GB)에서 쓸 것만 뽑아 parquet 로 만든다. 2026.08.25

    .venv/Scripts/python.exe ai/train/extract_bson.py

## 왜 원본을 여는가

지금까지 쓴 시간 단위 CSV 에는 **걸음·심박·칼로리 세 가지뿐**이었습니다.
원본에는 63,000,000 건이 들어 있고 그중에 우리가 찾던 것이 있습니다.

    heart_rate                     48,720,073   초 단위 심박
    Heart Rate Variability Details    220,512   ⭐ 실제 RMSSD — 불안의 표준 지표
    Wrist Temperature               4,372,241
    mindfulness_eda_data_sessions      16,070   피부 전기활동(EDA)
    Respiratory Rate Summary            3,000
    Stress Score                        1,911   Fitbit 자체 스트레스 점수

## 메모리 (RAM 32GB 에서 터지지 않게)

9.7GB 를 통째로 올리면 파이썬 객체로 부풀어 30GB 를 넘깁니다.
**길이 접두사로 문서를 하나씩 걸어가며** 필요한 것만 디코딩하고,
일정 개수마다 parquet 조각으로 떨어뜨립니다. 상주 메모리는 배치 하나뿐입니다.

## 심박은 두 벌로 뽑습니다

    hr_5min      전 구간 5분 집계(평균·표준편차·최소·최대·개수) — 기준선용
    hr_near      라벨 앞 6시간의 원시값                        — 단기 변동용

⚠ **단기 심박 변동이 HRV 대용입니다.** 라벨 직전 30분의 심박 분산은
  RMSSD 가 없는 구간에서도 계산됩니다(RMSSD 는 대부분 수면 중에만 찍힘).
"""
import struct
import sys
import time
import zipfile
from pathlib import Path

import bson
import numpy as np
import pandas as pd

SRC = Path("ai/data_raw/lifesnaps/mongo/fitbit.bson")
ZIP = Path("ai/data_raw/lifesnaps/rais_anonymized.zip")
OUT = Path("ai/data_raw/lifesnaps/parquet")
OUT.mkdir(parents=True, exist_ok=True)

NEAR_HOURS = 6          # 라벨 앞 몇 시간의 원시 심박을 남길지
HR_FLUSH = 4_000_000    # 이 개수마다 5분 집계로 접어 메모리를 비운다

#  뽑을 타입 → 출력 이름. heart_rate 는 따로 처리한다.
SIMPLE = {
    "Heart Rate Variability Details": "hrv",
    "Daily Heart Rate Variability Summary": "hrv_daily",
    "Stress Score": "stress",
    "Respiratory Rate Summary": "resp",
    "Daily SpO2": "spo2",
    "Wrist Temperature": "temp",
    "mindfulness_eda_data_sessions": "eda",
    "resting_heart_rate": "rhr",
    "sleep": "sleep",
}
WANTED = {k.encode() for k in SIMPLE} | {b"heart_rate"}


def label_windows():
    """라벨 시각 앞 NEAR_HOURS 시간 구간. (참가자, 시작, 끝) 목록."""
    docs = bson.decode_all(
        zipfile.ZipFile(ZIP).read("rais_anonymized/mongo_rais_anonymized/sema.bson"))
    rows = [(str(d["user_id"]), d["data"].get("COMPLETED_TS"))
            for d in docs if d["data"].get("MOOD") not in (None, "<no-response>")]
    lab = pd.DataFrame(rows, columns=["pid", "ts"])
    lab["ts"] = pd.to_datetime(lab["ts"], errors="coerce")
    lab = lab.dropna().drop_duplicates()
    #  ⚠ 구간을 미리 합쳐 정렬해 둔다. 행마다 선형 탐색하면 4800만 × 80 회가
    #    되어 못 끝납니다 — 아래 `near_mask` 가 searchsorted 로 한 번에 잽니다.
    win = {}
    for pid, g in lab.groupby("pid"):
        iv = sorted((t - pd.Timedelta(hours=NEAR_HOURS), t) for t in g.ts)
        merged = []
        for lo, hi in iv:
            if merged and lo <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
            else:
                merged.append((lo, hi))
        #  ⚠ 반드시 나노초로 못박습니다. pandas 3 은 to_datetime 기본 해상도를
        #    마이크로초로 바꿨는데 Timestamp.value 는 여전히 나노초라, 그대로
        #    비교하면 1000배 어긋나 아무것도 안 걸립니다(실제로 겪었습니다).
        win[pid] = (np.array(merged, dtype="datetime64[ns]")[:, 0].astype("int64"),
                    np.array(merged, dtype="datetime64[ns]")[:, 1].astype("int64"))
    return win


def near_mask(win, df):
    """구간 안에 드는 행을 참가자별로 한 번에 판정한다."""
    out = np.zeros(len(df), dtype=bool)
    tsv = df.ts.to_numpy("datetime64[ns]").astype("int64")   # 위 주석 참조
    for pid, idx in df.groupby("pid").indices.items():
        w = win.get(pid)
        if w is None:
            continue
        lo, hi = w
        t = tsv[idx]
        #  t 보다 크지 않은 마지막 구간을 찾아 그 끝을 넘지 않는지 본다
        j = np.searchsorted(lo, t, side="right") - 1
        ok = j >= 0
        out[idx[ok]] = t[ok] <= hi[j[ok]]
    return out


def fold_hr(rows):
    """원시 심박을 5분 집계로 접는다."""
    df = pd.DataFrame(rows, columns=["pid", "ts", "bpm", "conf"])
    df["ts"] = pd.to_datetime(df["ts"], format="ISO8601", errors="coerce")
    df = df.dropna(subset=["ts"])
    df["bin"] = df.ts.dt.floor("5min")
    return df.groupby(["pid", "bin"], as_index=False).agg(
        bpm_mean=("bpm", "mean"), bpm_std=("bpm", "std"),
        bpm_min=("bpm", "min"), bpm_max=("bpm", "max"), n=("bpm", "size"))


def main():
    win = label_windows()
    print(f"라벨 구간 {sum(len(v) for v in win.values())}개 · 참가자 {len(win)}\n")

    simple = {v: [] for v in SIMPLE.values()}
    hr_buf, hr_5min, hr_near = [], [], []
    total = kept = 0
    t0 = time.time()

    with open(SRC, "rb") as f:
        while True:
            head = f.read(4)
            if len(head) < 4:
                break
            n = struct.unpack("<i", head)[0]
            body = f.read(n - 4)
            total += 1

            #  ⚠ 디코딩 전에 바이트로 걸러낸다. 6300만 건을 전부 파이썬
            #    객체로 만들면 몇 시간이 걸린다.
            hit = None
            for w in WANTED:
                if w + b"\x00" in body:
                    hit = w
                    break
            if hit is None:
                continue

            d = bson.decode_all(head + body)[0]
            pid, typ, dat = str(d.get("id")), d.get("type"), d.get("data")
            if typ not in SIMPLE and typ != "heart_rate":
                continue
            kept += 1

            if typ == "heart_rate":
                v = dat.get("value") or {}
                hr_buf.append((pid, dat.get("dateTime"), v.get("bpm"), v.get("confidence")))
                if len(hr_buf) >= HR_FLUSH:
                    df = pd.DataFrame(hr_buf, columns=["pid", "ts", "bpm", "conf"])
                    df["ts"] = pd.to_datetime(df["ts"], format="ISO8601", errors="coerce")
                    df = df.dropna(subset=["ts"])
                    near = df[near_mask(win, df)]
                    if len(near):
                        hr_near.append(near)
                    hr_5min.append(fold_hr(hr_buf))
                    hr_buf = []
                    el = time.time() - t0
                    print(f"  {total/1e6:5.1f}M 문서 · {el:5.0f}초 · "
                          f"5분집계 {sum(len(x) for x in hr_5min)/1e6:.1f}M · "
                          f"근접원시 {sum(len(x) for x in hr_near):,}", flush=True)
            else:
                if isinstance(dat, dict):
                    simple[SIMPLE[typ]].append({"pid": pid, **dat})

    if hr_buf:
        df = pd.DataFrame(hr_buf, columns=["pid", "ts", "bpm", "conf"])
        df["ts"] = pd.to_datetime(df["ts"], format="ISO8601", errors="coerce")
        df = df.dropna(subset=["ts"])
        near = df[near_mask(win, df)]
        if len(near):
            hr_near.append(near)
        hr_5min.append(fold_hr(hr_buf))

    print(f"\n문서 {total:,} · 채택 {kept:,} · {time.time()-t0:.0f}초\n")

    h5 = pd.concat(hr_5min, ignore_index=True)
    #  조각마다 같은 5분 칸이 걸칠 수 있다 — 개수 가중으로 다시 접는다
    h5["_s"] = h5.bpm_mean * h5.n
    g = h5.groupby(["pid", "bin"], as_index=False).agg(
        _s=("_s", "sum"), n=("n", "sum"), bpm_std=("bpm_std", "mean"),
        bpm_min=("bpm_min", "min"), bpm_max=("bpm_max", "max"))
    g["bpm_mean"] = g._s / g.n
    g.drop(columns=["_s"]).to_parquet(OUT / "hr_5min.parquet", index=False)
    print(f"  hr_5min      {len(g):>10,}")

    if hr_near:
        hn = pd.concat(hr_near, ignore_index=True).drop_duplicates(subset=["pid", "ts"])
        hn.to_parquet(OUT / "hr_near.parquet", index=False)
        print(f"  hr_near      {len(hn):>10,}")

    for name, rows in simple.items():
        if not rows:
            print(f"  {name:12s} {'0':>10}")
            continue
        pd.DataFrame(rows).to_parquet(OUT / f"{name}.parquet", index=False)
        print(f"  {name:12s} {len(rows):>10,}")


if __name__ == "__main__":
    main()
