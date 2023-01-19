import io
import logging
import os
import sys

from keplergl import KeplerGl
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


PROJECT_DIR = os.getcwd()
if PROJECT_DIR not in sys.path:
    sys.path.append(PROJECT_DIR)

from src import configs  # noqa: E402,I100
from src import clustering_models  # noqa: E402,I100
from src import models  # noqa: E402,I100


st.set_page_config(
    page_icon="🚛",
    page_title="GPS clustering application",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache
def read_sample_gps():
    return pd.read_csv("src/gps_samples.csv")


@st.experimental_memo
def convert_df(df):
   return df.to_csv(index=False).encode('utf-8')

class Dashboard:

    @staticmethod
    def decode_uploaded_file_content(
        widget: st.runtime.uploaded_file_manager.UploadedFile,
    ) -> pd.DataFrame:
        """
        Function decoding uploaded csv file content into pandas dataframe

        Args:
        widget (st.runtime.uploaded_file_manager.UploadedFile): source file

        Returns:
        tp.Union[pd.DataFrame, None]: _description_
        """
        try:
            raw_content = widget.getvalue()
            string_content = raw_content.decode("utf-8")
            df = pd.read_csv(
                io.StringIO(string_content),
                delimiter=',',
                dtype=str,
            )
            return df
        except Exception as exc:
            msg = f"Failure at decoding uploaded csv file: {exc}"
            logging.error(msg)
            raise RuntimeError(msg)

    @staticmethod
    def aggregate_clusters(gps: pd.DataFrame) -> pd.DataFrame:
        clusters = gps \
            .groupby(["route_id", "cluster_id"]) \
            .agg(
                lat_centroid=("lat", "mean"),
                lon_centroid=("lon", "mean"),
                service_start_time=("datetime", "min"),
                service_end_time=("datetime", "max"),
                unix_start_time=("unixtime", "min"),
                unix_end_time=("unixtime", "max"),
            ).reset_index()
        clusters = clusters[clusters["cluster_id"] != -1.0].reset_index(drop=True)
        clusters["service_duration"] = clusters["unix_end_time"] - clusters["unix_start_time"]
        clusters.drop(columns=["unix_start_time", "unix_end_time"], inplace=True)
        return clusters

    @staticmethod
    def join_clusters_to_gps(
            gps: pd.DataFrame,
            clusters: pd.DataFrame,
    ) -> pd.DataFrame:
        return gps.merge(clusters, how="left")

    @staticmethod
    def render_map(left, gps: pd.DataFrame):
        with left:
            kepler_map = KeplerGl(
                data={"gps": gps.fillna("")},
                height=configs.MAP_HEIGHT,
                config=configs.kepler_map_config,
            )
            html = kepler_map._repr_html_(center_map=True, read_only=True)
            components.html(html, height=configs.MAP_HEIGHT)


def render_dashboard():

    st.write(configs.heading)
    gps = read_sample_gps()
    csv = convert_df(gps)
    st.download_button(
        "Press to Download GPS samples",
        csv,
        "gps_records_sample.csv",
        "text/csv",
        key='download-csv'
    )

    file_uploader_widget = st.file_uploader(
        label="GPS records file",
        type=["csv"],
        accept_multiple_files=False,
        key=None,
        help="Helper widget",
        on_change=None,
        disabled=False,
        label_visibility="visible",
    )

    if file_uploader_widget is not None:
        gps_records = Dashboard.decode_uploaded_file_content(file_uploader_widget)
        gps_records = clustering_models.vfhdbscan.predict(gps_records)
        agg_clusters = Dashboard.aggregate_clusters(gps_records.copy())
        gps_records = Dashboard.join_clusters_to_gps(gps=gps_records, clusters=agg_clusters)
        gps_records = models.validate_visualization_schema(gps_records)
        col_left, col_right = st.columns(2, gap="small")
        Dashboard.render_map(col_left, gps_records)
        col_right.dataframe(
            agg_clusters.rename(
                columns={"service_duration": "service_duration (seconds)"},
            ),
            height=configs.MAP_HEIGHT,
        )


if __name__ == "__main__":
    logging.info("Starting dashboard")
    render_dashboard()
