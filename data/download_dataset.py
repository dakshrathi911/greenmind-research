from pathlib import Path
from urllib.request import urlretrieve
from zipfile import ZipFile


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"

RAW_DIR.mkdir(parents=True, exist_ok=True)

ZIP_URL = (
    "https://archive.ics.uci.edu/"
    "ml/machine-learning-databases/00321/"
    "LD2011_2014.txt.zip"
)

ZIP_FILE = RAW_DIR / "LD2011_2014.txt.zip"
DATA_FILE = RAW_DIR / "LD2011_2014.txt"


def show_progress(block_num, block_size, total_size):
    if total_size <= 0:
        return

    downloaded = block_num * block_size
    percent = min(downloaded * 100 / total_size, 100)

    print(
        f"\rDownloading: {percent:6.2f}%",
        end="",
        flush=True
    )


print("GreenMind AI - UCI Electricity Dataset")
print("----------------------------------------")
print("Source: UCI Machine Learning Repository")
print("Dataset: ElectricityLoadDiagrams20112014")
print()

if DATA_FILE.exists():
    print("Dataset already exists.")
    print(DATA_FILE)

else:

    if not ZIP_FILE.exists():

        print("Downloading dataset...")
        print("Compressed size is approximately 249 MB.")
        print("This may take several minutes.")
        print()

        urlretrieve(
            ZIP_URL,
            ZIP_FILE,
            reporthook=show_progress
        )

        print("\n\nDownload complete.")

    else:
        print("ZIP file already exists.")

    print("\nExtracting dataset...")

    with ZipFile(ZIP_FILE, "r") as zip_file:

        members = zip_file.namelist()

        dataset_member = next(
            (
                member
                for member in members
                if member.endswith("LD2011_2014.txt")
            ),
            None
        )

        if dataset_member is None:
            raise FileNotFoundError(
                "LD2011_2014.txt was not found inside the ZIP file."
            )

        zip_file.extract(
            dataset_member,
            RAW_DIR
        )

        extracted_file = RAW_DIR / dataset_member

        if extracted_file != DATA_FILE:
            extracted_file.replace(DATA_FILE)

    print("Extraction complete.")

print()
print("Dataset ready:")
print(DATA_FILE)
print()
print("Next step: inspect the dataset before processing it.")