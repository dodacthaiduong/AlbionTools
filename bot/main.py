import click
from albion_bot.db.connection import get_db, close
from albion_bot.calibration.wizard import run_wizard, save_calibration
from albion_bot.logging_config import setup_logging


@click.group()
@click.option("--log-level", default="INFO", show_default=True, help="Logging level.")
def cli(log_level: str):
    """Albion Online auto-seller bot."""
    setup_logging(log_level)


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
@click.option("--profile", default="default", show_default=True, help="Calibration profile name.")
@click.option("--backup-dir", default=".", show_default=True, help="Directory for JSON backup.")
def calibrate(profile: str, backup_dir: str):
    """Run the calibration wizard."""
    try:
        cal = run_wizard(profile_name=profile)
        inserted_id = save_calibration(cal, backup_dir=backup_dir)
        click.echo(f"\nCalibration saved. MongoDB id: {inserted_id}")
        click.echo(f"JSON backup: {backup_dir}/calibration_{profile}.json")
    except Exception as e:
        click.echo(f"Calibration failed: {e}", err=True)
        raise SystemExit(1)
    finally:
        close()


@cli.command("calibrate-server")
def calibrate_server():
    """Run the click capture server for GUI calibration."""
    from albion_bot.calibration.capture_server import run_capture_server
    try:
        run_capture_server()
    except KeyboardInterrupt:
        click.echo("\nCapture server stopped.")
    finally:
        close()



    """Scan inventory and save items to MongoDB."""
    from albion_bot.inventory.scanner import scan_inventory
    try:
        scan_inventory(profile=profile)
    except Exception as e:
        click.echo(f"Scan failed: {e}", err=True)
        raise SystemExit(1)
    finally:
        close()


@cli.command()
@click.option("--profile", default="default", show_default=True, help="Calibration profile name.")
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
