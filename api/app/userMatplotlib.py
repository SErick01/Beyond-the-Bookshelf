import os
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_year_data(user_id: str, year: int):
    start = f"{year}-01-01"
    end = f"{year + 1}-01-01"

    comp_res = (
        supabase.table("completions")
        .select("work_id, finished_at")
        .eq("user_id", user_id)
        .gte("finished_at", start)
        .lt("finished_at", end)
        .execute()
    )

    completions = comp_res.data or []
    if not completions:
        return pd.DataFrame(), pd.DataFrame()

    completions_df = pd.DataFrame(completions)
    completions_df["finished_at"] = pd.to_datetime(completions_df["finished_at"])
    work_ids = completions_df["work_id"].unique().tolist()

    ed_res = (
        supabase.table("editions")
        .select("work_id, page_count")
        .in_("work_id", work_ids)
        .execute()
    )

    ed_df = pd.DataFrame(ed_res.data or [])
    ed_df = ed_df.drop_duplicates("work_id")
    completions_df = completions_df.merge(ed_df, on="work_id", how="left")
    completions_df["page_count"] = completions_df["page_count"].fillna(0)

    wg_res = (
        supabase.table("work_genres")
        .select("work_id, genre_id")
        .in_("work_id", work_ids)
        .execute()
    )
    wg_df = pd.DataFrame(wg_res.data or [])
    g_res = supabase.table("genres").select("genre_id, name").execute()
    genres_df = pd.DataFrame(g_res.data or [])
    work_genres_df = wg_df.merge(genres_df, on="genre_id", how="left")

    return completions_df, work_genres_df


def plot_pages_per_month(completions_df, year, out_path):
    df = completions_df.copy()
    df["month"] = df["finished_at"].dt.month

    pages_per_month = (
        df.groupby("month")["page_count"]
        .sum()
        .reindex(range(1, 13), fill_value=0)
    )

    fig, ax = plt.subplots()
    ax.bar(range(1, 13), pages_per_month.values)

    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(
        ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
        rotation=45
    )
    
    ax.set_ylabel("Pages read")
    ax.set_xlabel("Month")
    ax.set_title(f"Pages read in {year}")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_genres_pie(completions_df, work_genres_df, year, out_path):
    if completions_df.empty or work_genres_df.empty:
        return

    read_work_ids = completions_df["work_id"].unique()
    df = work_genres_df[work_genres_df["work_id"].isin(read_work_ids)]

    counts = df["name"].value_counts()
    if counts.empty:
        return

    fig, ax = plt.subplots()
    ax.pie(counts.values, labels=counts.index, autopct="%1.1f%%", startangle=90)
    ax.set_title(f"Genres read in {year}")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_completion_timeline(completions_df, year, out_path):
    if completions_df.empty:
        return

    df = completions_df.sort_values("finished_at").copy()
    df["book_number"] = range(1, len(df) + 1)

    fig, ax = plt.subplots()
    ax.scatter(df["finished_at"], df["book_number"])
    ax.set_xlabel("Date finished")
    ax.set_ylabel("Book # finished")
    ax.set_title(f"Reading timeline {year}")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def create_yearly_charts(user_id, year, output_dir="charts"):
    os.makedirs(output_dir, exist_ok=True)

    completions_df, work_genres_df = fetch_year_data(user_id, year)
    if completions_df.empty:
        return {}

    pages_path = os.path.join(output_dir, f"pages_{user_id}_{year}.png")
    genres_path = os.path.join(output_dir, f"genres_{user_id}_{year}.png")
    timeline_path = os.path.join(output_dir, f"timeline_{user_id}_{year}.png")

    plot_pages_per_month(completions_df, year, pages_path)
    plot_genres_pie(completions_df, work_genres_df, year, genres_path)
    plot_completion_timeline(completions_df, year, timeline_path)

    return {
        "pages": pages_path,
        "genres": genres_path,
        "timeline": timeline_path,
    }
