"""
담양군 빈집 데이터 API 서버 (FastAPI)

무엇을 하는 서버인가:
- damyang_final.csv 파일을 읽어서, 웹 요청이 오면 JSON으로 돌려준다
- 지금까지 만든 지오코딩 파이프라인의 결과물을, 웹에서 접근 가능하게 만드는 첫 단계

실행 방법:
1. 이 파일과 damyang_final.csv를 같은 폴더에 둔다
2. 터미널에서: pip3 install fastapi uvicorn pandas
3. 터미널에서: uvicorn main:app --reload
4. 브라우저에서 http://127.0.0.1:8000/houses 접속하면 데이터가 JSON으로 보인다
5. http://127.0.0.1:8000/docs 접속하면 API 문서(테스트 화면)가 자동으로 생성되어 있다
"""

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="담양군 빈집 API")

# 프론트엔드(React 등 다른 주소에서 실행되는 화면)에서 이 API를 호출할 수 있도록 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class UTF8JSONResponse(JSONResponse):
    """한글이 브라우저에서 깨지지 않도록, 응답 헤더에 UTF-8 인코딩을 명시하는 응답 클래스.
    기본 JSONResponse는 charset을 명시하지 않아서, 브라우저가 인코딩을 잘못 추측해
    한글이 깨져 보이는 경우가 있다."""

    media_type = "application/json; charset=utf-8"

CSV_PATH = "damyang_final.csv"


def load_houses():
    """CSV를 읽어서 파이썬이 다루기 쉬운 형태(딕셔너리 리스트)로 반환."""
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    # NaN(빈 값)이 있으면 JSON으로 변환할 때 오류가 나므로 빈 문자열로 치환
    df = df.fillna("")
    return df.to_dict(orient="records")


@app.get("/", response_class=UTF8JSONResponse)
def root():
    """서버가 살아있는지 확인용 기본 페이지."""
    return {"message": "담양군 빈집 API 서버가 동작 중입니다. /houses 에서 데이터를 확인하세요."}


@app.get("/houses", response_class=UTF8JSONResponse)
def get_houses(읍면: str | None = None, 용도: str | None = None):
    """빈집 목록을 반환한다.
    - 읍면 파라미터를 주면 해당 읍면만 필터링 (예: /houses?읍면=담양읍)
    - 용도 파라미터를 주면 해당 용도가 1위인 빈집만 필터링 (예: /houses?용도=주거)
    - 둘 다 안 주면 전체 405건을 반환
    """
    houses = load_houses()

    if 읍면:
        houses = [h for h in houses if h.get("읍면") == 읍면]
    if 용도:
        houses = [h for h in houses if h.get("1위용도") == 용도]

    return {"count": len(houses), "houses": houses}


@app.get("/houses/summary", response_class=UTF8JSONResponse)
def get_summary():
    """읍면별, 1위 용도별 요약 통계."""
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    by_usage = df["1위용도"].value_counts().to_dict()
    by_eupmyeon = df["읍면"].value_counts().to_dict()
    return {
        "전체건수": len(df),
        "용도별건수": by_usage,
        "읍면별건수": by_eupmyeon,
    }
