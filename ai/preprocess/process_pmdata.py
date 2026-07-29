import pandas as pd
import json
import os

def process_pmdata_sleep(sleep_json_path):
    """
    PMData fitbit/sleep.json 수면 파싱 함수
    """
    if not os.path.exists(sleep_json_path):
        print(f"❌ 수면 파일 없음: {sleep_json_path}")
        return None

    with open(sleep_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    # levels 컬럼 내 deep, light, rem, wake 분 단위 추출
    def parse_sleep_levels(row):
        try:
            summary = row.get('summary', {})
            deep_min = summary.get('deep', {}).get('minutes', 0)
            light_min = summary.get('light', {}).get('minutes', 0)
            rem_min = summary.get('rem', {}).get('minutes', 0)
            wake_min = summary.get('wake', {}).get('minutes', 0)
        except Exception:
            deep_min, light_min, rem_min, wake_min = 0, 0, 0, 0
        return pd.Series([deep_min, light_min, rem_min, wake_min])

    df[['deep_sleep_min', 'light_sleep_min', 'rem_sleep_min', 'wake_min']] = df['levels'].apply(parse_sleep_levels)

    selected_cols = [
        'dateOfSleep', 'duration', 'efficiency', 
        'minutesAsleep', 'deep_sleep_min', 'light_sleep_min', 
        'rem_sleep_min', 'wake_min'
    ]
    df_sub = df[selected_cols].copy()

    # duration (ms -> min) 단위 변환
    df_sub['duration_min'] = df_sub['duration'] / (1000 * 60)

    # 파생 비율 피처 생성 (0 나누기 방지)
    df_sub['minutesAsleep_safe'] = df_sub['minutesAsleep'].replace(0, 1)
    df_sub['rem_ratio'] = (df_sub['rem_sleep_min'] / df_sub['minutesAsleep_safe']) * 100
    df_sub['deep_ratio'] = (df_sub['deep_sleep_min'] / df_sub['minutesAsleep_safe']) * 100
    df_sub['wake_ratio'] = (df_sub['wake_min'] / df_sub['duration_min']) * 100

    final_cols = [
        'dateOfSleep', 'duration_min', 'minutesAsleep', 'efficiency',
        'deep_sleep_min', 'light_sleep_min', 'rem_sleep_min', 'wake_min',
        'deep_ratio', 'rem_ratio', 'wake_ratio'
    ]
    return df_sub[final_cols].copy()


def process_pmdata_heart_rate(hr_json_path):
    """
    PMData fitbit/heart_rate.json 심박수 및 HRV(SDNN) 파싱 함수
    """
    if not os.path.exists(hr_json_path):
        print(f"❌ 심박수 파일 없음: {hr_json_path}")
        return None

    with open(hr_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    df_hr = pd.DataFrame(data)

    # 날짜 추출 (YYYY-MM-DD)
    df_hr['dateOfSleep'] = pd.to_datetime(df_hr['dateTime']).dt.strftime('%Y-%m-%d')

    # bpm 수치 추출
    if isinstance(df_hr['value'].iloc[0], dict):
        df_hr['bpm'] = df_hr['value'].apply(lambda x: x.get('bpm', 0) if isinstance(x, dict) else x)
    else:
        df_hr['bpm'] = df_hr['value']

    # 일별 평균 심박수(avg_hr) 및 심박변이도(hrv_sdnn) 집계
    hr_summary = df_hr.groupby('dateOfSleep').agg(
        avg_hr=('bpm', 'mean'),
        hrv_sdnn=('bpm', 'std')  # 심박수 표준편차 = HRV 프록시 지표
    ).reset_index()

    return hr_summary.round(2)


if __name__ == "__main__":
    # PMData p01 파일 경로
    sleep_json_path = './osfstorage-archive/PMData/p01/fitbit/sleep.json'
    hr_json_path = './osfstorage-archive/PMData/p01/fitbit/heart_rate.json'
    output_csv = './pmdata_sleep_features.csv'

    print("🚀 [PMData] 수면 및 심박수/HRV 통합 전처리 시작...")
    df_sleep = process_pmdata_sleep(sleep_json_path)
    df_hr = process_pmdata_heart_rate(hr_json_path)

    if df_sleep is not None:
        if df_hr is not None:
            # 수면 데이터 + 심박수 데이터 날짜 기준 병합 (Left Join)
            df_final = pd.merge(df_sleep, df_hr, on='dateOfSleep', how='left')
        else:
            df_final = df_sleep

        # 결측치 보간 및 소수점 정돈
        df_final = df_final.fillna(df_final.mean(numeric_only=True)).round(2)

        print("\n=== 🎉 PMData 통합 Feature Matrix 완성 ===")
        print(df_final.head())
        print(f"\n최종 데이터 크기: {df_final.shape} (행, 열)")

        df_final.to_csv(output_csv, index=False)
        print(f"\n✅ '{output_csv}' 업데이트 완료 (수면 + avg_hr + hrv_sdnn 포함)")