
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------
# 1. 페이지 설정
# ---------------------------------------------
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="🏘️",
    layout="wide",
)

CSV_URL = (
    "https://raw.githubusercontent.com/"
    "seok3863/wasd/main/population_ts_yearly_gender.zip"
)

# 따뜻한 색상 테마
st.markdown(
    """
    <style>
    .stApp {
        background-color: #FFF8F0;
    }
    h1, h2, h3 {
        color: #80533D;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🏘️ 동네별 인구 피라미드")
st.caption("우리 동네의 나이별 남녀 인구를 확인해 보세요.")


# ---------------------------------------------
# 2. 데이터 불러오기
# ---------------------------------------------
@st.cache_data
def load_data():
    # URL이 .zip으로 끝나므로 pandas가 ZIP 압축을 자동으로 판별합니다.
    data = pd.read_csv(CSV_URL, compression="infer")

    # 열 이름 앞뒤의 공백을 제거합니다.
    data.columns = data.columns.astype(str).str.strip()

    # 반드시 있어야 하는 열을 확인합니다.
    required = ["연도", "시도", "시군구", "동"]
    missing = [col for col in required if col not in data.columns]

    if missing:
        raise ValueError(f"필수 열을 찾을 수 없습니다: {missing}")

    # 연도를 숫자로 변환하고, 유효하지 않은 행은 제거합니다.
    data["연도"] = pd.to_numeric(data["연도"], errors="coerce")
    data = data.dropna(subset=["연도"]).copy()
    data["연도"] = data["연도"].astype(int)

    if data.empty:
        raise ValueError("데이터에 유효한 연도가 없습니다.")

    # 데이터에 들어 있는 연도 중 가장 최신 연도만 사용합니다.
    latest_year = int(data["연도"].max())
    data = data[data["연도"] == latest_year].copy()

    # 지역 이름이 비어 있으면 빈 문자열로 처리합니다.
    for col in ["시도", "시군구", "동"]:
        data[col] = data[col].fillna("").astype(str).str.strip()

    return data, latest_year


try:
    df, latest_year = load_data()
except Exception as e:
    st.error("데이터를 불러오지 못했습니다.")
    st.exception(e)
    st.stop()

st.info(f"📅 표시 중인 자료: **{latest_year}년**")


# ---------------------------------------------
# 3. 0세부터 100세 이상까지 나이 목록 만들기
# ---------------------------------------------
ages = [f"{age}세" for age in range(100)] + ["100세 이상"]

# 각 나이에 해당하는 남녀 인구 열 이름을 만듭니다.
male_cols = [f"남_{age}" for age in ages]
female_cols = [f"여_{age}" for age in ages]
population_cols = male_cols + female_cols

# 모든 인구 열이 실제 데이터에 있는지 검사합니다.
missing_cols = [col for col in population_cols if col not in df.columns]

if missing_cols:
    st.error(
        "다음 인구 열을 찾을 수 없습니다: "
        + ", ".join(missing_cols[:10])
    )
    st.stop()

# 인구 데이터에 쉼표가 있더라도 숫자로 변환합니다.
for col in population_cols:
    df[col] = pd.to_numeric(
        df[col].astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    ).fillna(0)


# ---------------------------------------------
# 4. 시도 → 시군구 → 동 드롭다운
# ---------------------------------------------
st.subheader("📍 지역 선택")

col1, col2, col3 = st.columns(3)

with col1:
    sido_options = sorted(df["시도"].unique().tolist())
    selected_sido = st.selectbox("① 시도", sido_options)

# 선택한 시도에 포함된 시군구만 표시합니다.
df_sido = df[df["시도"] == selected_sido]

with col2:
    sigungu_options = sorted(df_sido["시군구"].unique().tolist())
    selected_sigungu = st.selectbox("② 시군구", sigungu_options)

# 선택한 시군구에 포함된 동만 표시합니다.
df_sigungu = df_sido[df_sido["시군구"] == selected_sigungu]

with col3:
    dong_options = sorted(df_sigungu["동"].unique().tolist())
    selected_dong = st.selectbox("③ 동", dong_options)


# ---------------------------------------------
# 5. 선택한 지역의 인구 계산
# ---------------------------------------------
selected = df_sigungu[df_sigungu["동"] == selected_dong]

if selected.empty:
    st.warning("선택한 지역의 데이터가 없습니다.")
    st.stop()

# 동일 지역에 여러 행이 있을 경우 나이별로 합산합니다.
male_population = selected[male_cols].sum(axis=0).tolist()
female_population = selected[female_cols].sum(axis=0).tolist()

# 남성은 음수로 만들어 왼쪽에 표시합니다.
male_left = [-int(value) for value in male_population]

# 여성은 양수 그대로 오른쪽에 표시합니다.
female_right = [int(value) for value in female_population]

male_total = int(sum(male_population))
female_total = int(sum(female_population))
total_population = male_total + female_total


# ---------------------------------------------
# 6. 인구 요약
# ---------------------------------------------
st.divider()
st.subheader(
    f"📊 {selected_sido} {selected_sigungu} {selected_dong}"
)

metric1, metric2, metric3 = st.columns(3)

metric1.metric("전체 인구", f"{total_population:,}명")
metric2.metric("남성 인구", f"{male_total:,}명")
metric3.metric("여성 인구", f"{female_total:,}명")


# ---------------------------------------------
# 7. Plotly 인구 피라미드
# ---------------------------------------------
fig = go.Figure()

# 남성 막대: 음수이므로 중앙의 0을 기준으로 왼쪽에 그려집니다.
fig.add_trace(
    go.Bar(
        name="남성",
        x=male_left,
        y=ages,
        orientation="h",
        marker_color="#D78968",
        customdata=male_population,
        hovertemplate=(
            "나이: %{y}<br>"
            "남성 인구: %{customdata:,}명"
            "<extra></extra>"
        ),
    )
)

# 여성 막대: 양수이므로 오른쪽에 그려집니다.
fig.add_trace(
    go.Bar(
        name="여성",
        x=female_right,
        y=ages,
        orientation="h",
        marker_color="#E7A9B7",
        hovertemplate=(
            "나이: %{y}<br>"
            "여성 인구: %{x:,}명"
            "<extra></extra>"
        ),
    )
)

# 남녀의 가로축 범위를 대칭으로 설정합니다.
largest_population = max(
    max(male_population, default=0),
    max(female_population, default=0),
)
axis_limit = max(1, int(largest_population * 1.1))

# 중요: 나이 축은 목록 순서대로 고정합니다.
# categoryarray의 첫 항목인 0세가 맨 아래에,
# 마지막 항목인 100세 이상이 맨 위에 표시됩니다.
# 축 반전이나 값 크기순 정렬 옵션은 사용하지 않습니다.
fig.update_layout(
    title={
        "text": f"{selected_dong} 나이별 남녀 인구",
        "x": 0.5,
        "xanchor": "center",
        "font": {"size": 23, "color": "#80533D"},
    },
    barmode="overlay",
    bargap=0.12,
    height=1500,
    paper_bgcolor="#FFF8F0",
    plot_bgcolor="#FFFCF8",
    font={"color": "#624A3D"},
    legend={
        "title": "성별",
        "orientation": "h",
        "x": 0.5,
        "xanchor": "center",
        "y": 1.03,
    },
    margin={"l": 95, "r": 35, "t": 100, "b": 65},
    xaxis={
        "title": "인구 (명)",
        "range": [-axis_limit, axis_limit],
        "zeroline": True,
        "zerolinecolor": "#A58A78",
        "zerolinewidth": 2,
        "gridcolor": "#F0E4D9",
        "tickmode": "array",
        "tickvals": [
            -axis_limit,
            -(axis_limit // 2),
            0,
            axis_limit // 2,
            axis_limit,
        ],
        "ticktext": [
            f"{axis_limit:,}",
            f"{axis_limit // 2:,}",
            "0",
            f"{axis_limit // 2:,}",
            f"{axis_limit:,}",
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
    "나이 축은 아래 0세부터 위 100세 이상까지 순서대로 표시됩니다."
)


# ---------------------------------------------
# 8. 연령별 인구표와 CSV 다운로드
# ---------------------------------------------
with st.expander("📋 연령별 남녀 인구표 보기"):
    population_table = pd.DataFrame(
        {
            "나이": ages,
            "남성": [int(value) for value in male_population],
            "여성": [int(value) for value in female_population],
            "합계": [
                int(male) + int(female)
                for male, female in zip(
                    male_population, female_population
                )
            ],
        }
    )

    st.dataframe(
        population_table,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        label="📥 연령별 인구표 CSV 다운로드",
        data=population_table.to_csv(
            index=False,
            encoding="utf-8-sig",
        ),
        file_name=(
            f"{selected_sido}_{selected_sigungu}_"
            f"{selected_dong}_{latest_year}.csv"
        ),
        mime="text/csv",
    )

st.caption("자료 출처: 제공된 GitHub 인구 데이터")
