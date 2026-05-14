import click
from albion_bot.db.connection import get_db, close
from albion_bot.calibration.wizard import run_wizard, save_calibration


@click.group()
def cli():
    """Albion Online auto-seller bot."""
    pass


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


@cli.command()
def scan():
    """Scan inventory (M2)."""
    click.echo("Inventory scan not yet implemented.")


@cli.command()
def sell():
    """Start the selling loop (M3)."""
    click.echo("Selling loop not yet implemented.")


if __name__ == "__main__":
    cli()
