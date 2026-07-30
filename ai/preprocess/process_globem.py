import pandas as pd
import os

def process_globem_full(sample_base_path):
    """
    GLOBEM 수면(sleep) + 걸음수(steps) + 우울라벨(dep_endterm) 통합 파싱 함수

    ※ 스크린타임(screen.csv)은 의도적으로 제외합니다. 아래 주석 참고.
    """
    print(f"🚀 [GLOBEM] 라이프로그 전처리 시작...")

    # 1. 파일 경로 설정
    sleep_path = os.path.join(sample_base_path, 'FeatureData', 'sleep.csv')
    steps_path = os.path.join(sample_base_path, 'FeatureData', 'steps.csv')
    survey_path = os.path.join(sample_base_path, 'SurveyData', 'dep_endterm.csv')

    # -----------------------------------------------------------------
    # 스크린타임(screen.csv)을 쓰지 않는 이유 — 다시 넣지 마세요
    #
    # 서비스가 만들 수 없는 피처로 학습하면 배포 시 그 자리가 비어
    # 성능이 나오지 않습니다. LISN 은 폰 사용량을 수집하지 않습니다.
    #   - LIFELOG_METRICS 에 스크린타임 컬럼이 없음 (db/schema.sql)
    #   - Health Connect 는 스크린타임을 제공하지 않음
    #     (UsageStatsManager 는 별도 권한 영역이며 수집 범위 밖)
    #
    # 폰 사용량을 정식 수집 항목으로 추가하기로 결정한다면, 그때
    # 스키마·요구사항정의서·동의 항목을 먼저 고치고 되살리세요.
    # -----------------------------------------------------------------

    # 2. 파일 존재 여부 확인
    if not all([os.path.exists(p) for p in [sleep_path, steps_path, survey_path]]):
        print("❌ 필수 GLOBEM 파일 경로를 확인해 주세요.")
        return None

    # 3. 수면 데이터 파싱
    df_sleep = pd.read_csv(sleep_path)
    sleep_cols = [c for c in df_sleep.columns if 'asleep' in c or 'awake' in c]
    df_sleep_sub = df_sleep[['pid', 'date'] + sleep_cols[:4]].copy()

    # 4. 걸음 수 데이터 파싱
    df_steps = pd.read_csv(steps_path)
    steps_cols = [c for c in df_steps.columns if 'steps' in c or 'active' in c or 'bout' in c]
    df_steps_sub = df_steps[['pid', 'date'] + steps_cols[:4]].copy()

    # 5. 수면 + 걸음 수 병합
    df_features = pd.merge(df_sleep_sub, df_steps_sub, on=['pid', 'date'], how='inner')

    # 6. 우울증 정답 라벨(dep_endterm.csv) 매핑
    df_survey = pd.read_csv(survey_path)
    df_final = pd.merge(df_features, df_survey[['pid', 'BDI2', 'dep']], on='pid', how='left')

    # 7. 결측치 보간 및 수치 정돈
    df_final = df_final.fillna(df_final.mean(numeric_only=True))

    return df_final


if __name__ == "__main__":
    sample_base = './GLOBEM-main/data_raw/INS-W-sample_1'
    output_csv = './feature_matrix_sample.csv'

    df_globem_final = process_globem_full(sample_base)

    if df_globem_final is not None:
        print("\n=== 🎉 GLOBEM 통합 Feature Matrix 완성 (수면 + 걸음수 + BDI-II 라벨) ===")
        print(df_globem_final.head())
        print(f"\n최종 데이터 크기: {df_globem_final.shape} (행, 열)")

        df_globem_final.to_csv(output_csv, index=False)
        print(f"\n✅ '{output_csv}' 업데이트 완료!")