import pandas as pd
import os

def process_globem_full(sample_base_path):
    """
    GLOBEM 수면(sleep) + 걸음수(steps) + 스크린타임(screen) + 우울라벨(dep_endterm) 통합 파싱 함수
    """
    print(f"🚀 [GLOBEM] 라이프로그 & 스크린타임 통합 전처리 시작...")
    
    # 1. 파일 경로 설정
    sleep_path = os.path.join(sample_base_path, 'FeatureData', 'sleep.csv')
    steps_path = os.path.join(sample_base_path, 'FeatureData', 'steps.csv')
    screen_path = os.path.join(sample_base_path, 'FeatureData', 'screen.csv')
    survey_path = os.path.join(sample_base_path, 'SurveyData', 'dep_endterm.csv')

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

    # 5. 수면 + 걸음 수 1차 병합
    df_features = pd.merge(df_sleep_sub, df_steps_sub, on=['pid', 'date'], how='inner')

    # 6. 스크린타임(screen.csv) 데이터 존재 시 파싱 및 추가 병합
    if os.path.exists(screen_path):
        print("📱 스크린타임(screen.csv) 피처 파싱 및 병합 중...")
        df_screen = pd.read_csv(screen_path)
        # 스크린타임, 화면 켜짐 관련 핵심 컬럼 선별
        screen_cols = [c for c in df_screen.columns if 'screen' in c or 'unlock' in c or 'dur' in c]
        if len(screen_cols) > 0:
            df_screen_sub = df_screen[['pid', 'date'] + screen_cols[:3]].copy()
            df_features = pd.merge(df_features, df_screen_sub, on=['pid', 'date'], how='left')

    # 7. 우울증 정답 라벨(dep_endterm.csv) 매핑
    df_survey = pd.read_csv(survey_path)
    df_final = pd.merge(df_features, df_survey[['pid', 'BDI2', 'dep']], on='pid', how='left')

    # 8. 결측치 보간 및 수치 정돈
    df_final = df_final.fillna(df_final.mean(numeric_only=True))

    return df_final


if __name__ == "__main__":
    sample_base = './GLOBEM-main/data_raw/INS-W-sample_1'
    output_csv = './feature_matrix_sample.csv'

    df_globem_final = process_globem_full(sample_base)

    if df_globem_final is not None:
        print("\n=== 🎉 GLOBEM 통합 Feature Matrix 완성 (스크린타임 포함) ===")
        print(df_globem_final.head())
        print(f"\n최종 데이터 크기: {df_globem_final.shape} (행, 열)")

        df_globem_final.to_csv(output_csv, index=False)
        print(f"\n✅ '{output_csv}' 업데이트 완료!")