"""Build an executable for NexGen-BBPro using PyInstaller."""
import PyInstaller.__main__


def main() -> None:
    """Run PyInstaller to create a standalone executable."""
    PyInstaller.__main__.run(
        [
            "main.py",
            "--onefile",
            "--name",
            "NexGen-BBPro",
        ]
    )


if __name__ == "__main__":
    main()
