import click

from albion_bot.calibration.wizard import save_calibration
from albion_bot.db.connection import close, get_db
from albion_bot.debug_logger import DEBUG_MODE, tao_bao_cao_loi
from albion_bot.logging_config import setup_logging


@click.group()
@click.option("--log-level", default="INFO", show_default=True, help="Logging level.")
def cli(log_level: str):
    """Albion Online auto-seller bot."""
    setup_logging(log_level)
    if DEBUG_MODE:
        click.echo("[DEBUG MODE] Chế độ debug đang BẬT — log chi tiết sẽ được ghi ra file debug.log")


@cli.command()
def status():
    """Check MongoDB connection and bot status."""
    try:
        db = get_db()
        db.command("ping")
        click.echo("MongoDB: connected")
    except Exception as e:
        click.echo(f"MongoDB: error — {e}", err=True)
    finally:
        close()


@cli.command()
@click.option(
    "--profile", default="default", show_default=True, help="Calibration profile name."
)
@click.option(
    "--backup-dir", default=".", show_default=True, help="Directory for JSON backup."
)
def calibrate(profile: str, backup_dir: str):
    """Run the calibration wizard."""
    click.echo(
        "Calibration has moved to the desktop GUI. Run `make bot-gui` to launch it."
    )


@cli.command()
def gui():
    """Launch the desktop GUI."""
    from albion_bot.gui.app import launch

    launch()


@cli.command()
@click.option(
    "--profile", default="default", show_default=True, help="Calibration profile name."
)
def sell(profile: str):
    """Start the selling loop."""
    import signal

    from albion_bot.selling.loop import run_sell_loop

    stop_flag = [False]

    def _handle_signal(sig, frame):
        click.echo("\nStop requested, finishing current cycle...")
        stop_flag[0] = True

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        run_sell_loop(profile=profile, stop_flag=stop_flag)
    except Exception as e:
        click.echo(f"Sell loop error: {e}", err=True)
        raise SystemExit(1)
    finally:
        close()


if __name__ == "__main__":
    cli()
