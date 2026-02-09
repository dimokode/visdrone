import gdown

def download_weights():
    url_with_weights = "https://drive.google.com/drive/folders/1TNvJLqJkELUV_5ih9Izdcm8lBc4M_9Em?usp=drive_link"

    gdown.download_folder(url_with_weights, output="./weights", quiet=False)

if __name__ == "__main__":
    download_weights()