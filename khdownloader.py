import asyncio
import aiohttp
import aiofiles
from bs4 import BeautifulSoup
import os
from urllib.parse import unquote
import re

async def download_file(session, url, save_dir):
    try:
        os.makedirs(save_dir, exist_ok=True)

        async with session.get(url) as response:
            response.raise_for_status()

            decoded_url = unquote(url)
            filename = os.path.basename(decoded_url)

            if 'Content-Disposition' in response.headers:
                content_disposition = response.headers['Content-Disposition']
                if 'filename=' in content_disposition:
                    filename = content_disposition.split('filename=')[1].strip('"')
            #print(sanitize_filename(filename), filename)
            save_path = os.path.join(save_dir, await sanitize_filename(filename))

            async with aiofiles.open(save_path, 'wb') as file:
                await file.write(await response.read())

        print(f"File downloaded and saved as: {save_path}")

    except aiohttp.ClientError as e:
        print(f"Error downloading file: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

async def process_song_link(session, song_link, file_extension, download_folder):
    async with session.get(song_link) as song_page_response:
        song_page_content = await song_page_response.text()
        song_page_soup = BeautifulSoup(song_page_content, 'html.parser')
        paragraphs = song_page_soup.find_all('p')

        for paragraph in paragraphs:
            span = paragraph.find('span', class_='songDownloadLink')
            if span:
                anchor = paragraph.find('a')
                if anchor and 'href' in anchor.attrs:
                    if anchor['href'].endswith(file_extension):
                        print(f"Downloading {file_extension} from link {anchor['href']}")
                        await download_file(session, anchor['href'], download_folder)

async def main():
    webpage_url = input("Input KHinsider URL: ")
    file_extension = input("What file extension do you want to download?: ")

    async with aiohttp.ClientSession() as session:
        async with session.get(webpage_url) as response:
            content = await response.text()
            soup = BeautifulSoup(content, 'html.parser')

        # Extract folder name from the first h2 in the pageContent div
        page_content_div = soup.find('div', {'id': 'pageContent'})
        if page_content_div:
            first_h2 = page_content_div.find('h2')
            if first_h2:
                folder_name = first_h2.text.strip()
            else:
                folder_name = "Unknown Album"
        else:
            folder_name = "Unknown Album"

        # Create the download folder path
        download_folder = os.path.join("downloads", folder_name)

        song_links = []
        table = soup.find('table', {'id': 'songlist'})
        if table:
            for td in table.find_all('td', {'class': 'playlistDownloadSong'}):
                link = td.find('a')
                if link:
                    song_links.append("https://downloads.khinsider.com" + link['href'])

        tasks = [process_song_link(session, song_link, file_extension, download_folder) for song_link in song_links]
        await asyncio.gather(*tasks)
        
async def sanitize_filename(filename: str) -> str:
    # Define a regex pattern to match invalid characters
    # Here we allow alphanumeric characters, underscores, hyphens, and periods
    # You can modify this regex to include or exclude more characters as needed
    valid_filename = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', filename)
    
    # Optionally, you can also limit the length of the filename
    # For example, you might want to keep it under 255 characters
    max_length = 255
    if len(valid_filename) > max_length:
        valid_filename = valid_filename[:max_length]
    
    return valid_filename

if __name__ == "__main__":
    asyncio.run(main())