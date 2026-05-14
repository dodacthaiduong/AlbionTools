import click
from albion_bot.db.connection import get_db, close


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
def calibrate():
    """Run the calibration wizard (M1)."""
    click.echo("Calibration wizard not yet implemented.")


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
