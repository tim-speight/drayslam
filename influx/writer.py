import os

from influxdb_client import InfluxDBClient, Point

from dslam.model import DSLAMStatus


class InfluxWriter:

    def __init__(self) -> None:

        self.client = InfluxDBClient(
            url=os.environ["INFLUX_URL"],
            token=os.environ["INFLUX_TOKEN"],
            org=os.environ["INFLUX_ORG"],
        )

        self.bucket = os.environ["INFLUX_BUCKET"]

        self.write_api = self.client.write_api()

    def write(self, status: DSLAMStatus) -> None:
        point = (
            Point("dslam_metrics")
            .tag("profile", status.profile)
            .tag("state", status.state)
            .tag("overall_status", status.overall_status)
            .field("device_up", int(status.device_up))
            .field("upstream_kbps", status.upstream_kbps)
            .field("downstream_kbps", status.downstream_kbps)
            .field("snr_up", status.snr_up)
            .field("snr_down", status.snr_down)
            .field("uptime_length", len(status.uptime))
        )

        self.write_api.write(
            bucket=self.bucket,
            record=point,
        )

    def close(self) -> None:
        """Flush the batching write API before shutdown."""
        self.write_api.close()
        self.client.close()
