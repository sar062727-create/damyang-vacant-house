"""
빈집 개별 데이터(405건) + 읍면별 시설 점수(12개) 합치기
- 입력1: damyang_geocoded.csv (빈집 405건, 위치주소·위도·경도)
- 입력2: eupmyeon_facilities.csv (읍면 12개, 주거/관광 점수·추천용도)
- 출력: damyang_final.csv (빈집 405건 각각에 추천용도가 붙은 최종 파일)

API 호출 없음 — 이미 만든 두 파일을 '읍면' 기준으로 합치기만 함.
"""

import pandas as pd

HOUSES_CSV = "damyang_geocoded.csv"
FACILITIES_CSV = "eupmyeon_facilities.csv"
OUTPUT_CSV = "damyang_final.csv"


def main():
    houses = pd.read_csv(HOUSES_CSV, encoding="utf-8-sig")
    facilities = pd.read_csv(FACILITIES_CSV, encoding="utf-8-sig")

    # 빈집 주소에서 읍면 이름 추출 (예: "전라남도 담양군 담양읍 담주리" -> "담양읍")
    houses["읍면"] = houses["위치주소(지번 비공개)"].str.extract(r"담양군 (\S+[읍면])")

    # 읍면 기준으로 합치기 (빈집 개별 행 기준, 왼쪽 기준 병합이라 빈집 405건은 그대로 유지됨)
    merged = houses.merge(
        facilities[["읍면", "주거적합점수", "관광숙박적합점수", "추천용도"]],
        on="읍면",
        how="left",
    )

    merged.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print(f"완료: {OUTPUT_CSV} 저장 (총 {len(merged)}건)")
    print()
    print("추천용도별 빈집 개수:")
    print(merged["추천용도"].value_counts())
    print()
    print("샘플 5건:")
    print(merged[["위치주소(지번 비공개)", "읍면", "추천용도", "주거적합점수", "관광숙박적합점수"]].head(5).to_string())


if __name__ == "__main__":
    main()
