
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# -----------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="🏘️",
    layout="wide",
)

CSV_URL = "https://raw.githubusercontent.com/seok3863/wasd/main/wasd"

st.markdown("""
<style>
.stApp { background-color: #FFF9F2; }
h1, h2, h3 { color: #784B35; }
</style>
""", unsafe_allow_html=True)

st.title("🏘️ 동네별 인구 피라미드")
st.caption("시도와 동네를 선택해 나이별 남녀 인구를 살펴보세요.")


# -----------------------------------------------
# 2. CSV 읽기
# -----------------------------------------------
@st.cache_data
def load_data():
    # 압축 형식은 pandas가 자동으로 판별합니다.
    data = pd.read_csv(CSV_URL, compression="infer")
    data.columns = data.columns.astype(str).str.strip()

    required = ["연도", "시도", "시군구", "동"]
    missing = [c for c in required if c not in data.columns]

    if missing:
        raise ValueError(f"필수 열이 없습니다: {missing}")

    data["연도"] = pd.to_numeric(data["연도"], errors="coerce")
    data = data.dropna(subset=["연도"]).copy()
    data["연도"] = data["연도"].astype(int)

    # 데이터에 실제로 들어 있는 가장 최신 연도를 선택합니다.
    latest_year = int(data["연도"].max())
    data = data[data["연도"] == latest_year].copy()

    for col in ["시도", "시군구", "동"]:
        data[col] = data[col].fillna("").astype(str).str.strip()

    return data, latest_year


try:
    df, latest_year = load_data()
except Exception as e:
    st.error("데이터를 읽지 못했습니다. CSV 주소와 파일 형식을 확인해 주세요.")
    st.exception(e)
    st.stop()

st.info(f"📅 선택된 최신 자료: **{latest_year}년**")


# -----------------------------------------------
# 3. 나이별 인구 열 준비
# -----------------------------------------------
ages = [f"{i}세" for i in range(100)] + ["100세 이상"]

male_cols = [f"남_{age}" for age in ages]
female_cols = [f"여_{age}" for age in ages]

# 필요한 인구 열이 있는지 확인합니다.
missing_population_cols = [
    c for c in male_cols + female_cols if c not in df.columns
]

if missing_population_cols:
    st.error(
        "다음 인구 열을 CSV에서 찾을 수 없습니다: "
        + ", ".join(missing_population_cols[:10])
    )
    st.stop()

# 쉼표가 포함된 숫자도 처리합니다.
for col in male_cols + female_cols:
    df[col] = pd.to_numeric(
        df[col].astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    ).fillna(0)


# -----------------------------------------------
# 4. 시도 → 시군구 → 동 선택
# -----------------------------------------------
st.subheader("📍 지역 선택")

c1, c2, c3 = st.columns(3)

with c1:
    sido_options = sorted(df["시도"].unique().tolist())
    sido = st.selectbox("① 시도", sido_options)

df_sido = df[df["시도"] == sido]

with c2:
    sigungu_options = sorted(df_sido["시군구"].unique().tolist())
    sigungu = st.selectbox("② 시군구", sigungu_options)

df_sigungu = df_sido[df_sido["시군구"] == sigungu]

with c3:
    dong_options = sorted(df_sigungu["동"].unique().tolist())
    dong = st.selectbox("③ 동", dong_options)


# -----------------------------------------------
# 5. 선택한 지역의 인구 합계
# -----------------------------------------------
selected = df_sigungu[df_sigungu["동"] == dong]

if selected.empty:
    st.warning("선택한 지역의 데이터가 없습니다.")
    st.stop()

# 같은 지역에 여러 행이 있다면 연령별로 합산합니다.
male = selected[male_cols].sum(axis=0).tolist()
female = selected[female_cols].sum(axis=0).tolist()

# 남성은 음수로 만들어 왼쪽에 표시합니다.
male_left = [-int(v) for v in male]
female_right = [int(v) for v in female]

male_total = int(sum(male))
female_total = int(sum(female))
all_total = male_total + female_total

st.subheader(f"📊 {sido} {sigungu} {dong}")

m1, m2, m3 = st.columns(3)
m1.metric("전체 인구", f"{all_total:,}명")
m2.metric("남성 인구", f"{male_total:,}명")
m3.metric("여성 인구", f"{female_total:,}명")


# -----------------------------------------------
# 6. 인구 피라미드
# -----------------------------------------------
fig = go.Figure()

fig.add_trace(go.Bar(
    name="남성",
    x=male_left,
    y=ages,
    orientation="h",
    marker_color="#D98968",
    customdata=male,
    hovertemplate="나이: %{y}<br>남성: %{customdata:,}명<extra></extra>",
))

fig.add_trace(go.Bar(
    name="여성",
    x=female_right,
    y=ages,
    orientation="h",
    marker_color="#E8A9B8",
    hovertemplate="나이: %{y}<br>여성: %{x:,}명<extra></extra>",
))

# 남녀 그래프의 가로축 범위를 대칭으로 맞춥니다.
largest = max(max(male, default=0), max(female, default=0))
limit = max(1, int(largest * 1.1))

# 중요: 나이 라벨을 직접 지정해 순서를 고정합니다.
# categoryarray의 첫 항목인 0세가 맨 아래에 표시됩니다.
# 축을 뒤집는 옵션이나 값 크기순 정렬은 사용하지 않습니다.
fig.update_layout(
    title={
        "text": f"{dong} 나이별 남녀 인구",
        "x": 0.5,
        "xanchor": "center",
    },
    barmode="overlay",
    bargap=0.12,
    height=1500,
    paper_bgcolor="#FFF9F2",
    plot_bgcolor="#FFFCF8",
    font={"color": "#60483B"},
    legend={
        "title": "성별",
        "orientation": "h",
        "x": 0.5,
        "xanchor": "center",
        "y": 1.03,
    },
    margin={"l": 90, "r": 35, "t": 100, "b": 65},
    xaxis={
        "title": "인구 (명)",
        "range": [-limit, limit],
        "zeroline": True,
        "zerolinecolor": "#A58A78",
        "gridcolor": "#F0E5DA",
        "tickmode": "array",
        "tickvals": [
            -limit, -limit // 2, 0, limit // 2, limit
        ],
        "ticktext": [
            f"{limit:,}",
            f"{limit // 2:,}",
            "0",
            f"{limit // 2:,}",
            f"{limit:,}",
        ],
    },
    yaxis={
        "title": "나이",
        "type": "category",
        "categoryorder": "array",
        "categoryarray": ages,
        "tickmode": "array",
        "tickvals": ages,
        "ticktext": ages,
        "showgrid": False,
        "automargin": True,
    },
)

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "왼쪽은 남성, 오른쪽은 여성입니다. "
    "세로축은 아래 0세부터 위 100세 이상까지 표시됩니다."
)


# -----------------------------------------------
# 7. 연령별 인구표 및 CSV 다운로드
# -----------------------------------------------
with st.expander("📋 연령별 인구표 보기"):
    table = pd.DataFrame({
        "나이": ages,
        "남성": [int(v) for v in male],
        "여성": [int(v) for v in female],
        "합계": [
            int(m) + int(f) for m, f in zip(male, female)
        ],
    })

    st.dataframe(table, use_container_width=True, hide_index=True)

    st.download_button(
        "📥 인구표 CSV 다운로드",
        data=table.to_csv(index=False, encoding="utf-8-sig"),
        file_name=f"{sido}_{sigungu}_{dong}_{latest_year}.csv",
        mime="text/csv",
    )

st.caption("자료 출처: GitHub 인구 데이터 CSV")
