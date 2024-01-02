import asyncio
from datetime import datetime
from pathlib import Path

from aiofile import async_open
from aiohttp import ClientSession
from aiohttp_retry import RetryClient, ExponentialRetry

from urllib.parse import urlparse

from sqlmodel import Session, select

from app.db import get_engine, Invoice, init_engine

semaphore = asyncio.Semaphore(10)
retry_options = ExponentialRetry(attempts=1)


async def download(client: RetryClient, invoice: Invoice, download_path: Path):
    try:
        async with semaphore, client.get(invoice.download_url) as response:
            response.raise_for_status()
            data = await response.read()
            async with async_open(download_path, "wb+") as afp:
                await afp.write(data)
        invoice.downloaded = True
    except Exception as e:
        print(e)
    finally:
        invoice.last_updated = datetime.now()


async def download_batch(batch: list[tuple[Invoice, Path]]):
    async with ClientSession() as downloader:
        client = RetryClient(downloader, retry_options=retry_options)
        tasks = []
        for (invoice, download_path) in batch:
            tasks.append(download(client, invoice, download_path))
        await asyncio.gather(*tasks)


async def download_invoices(condition):
    with Session(get_engine()) as session:
        query = select(Invoice).where(condition)
        invoices = session.scalars(query)

        batch = []

        for invoice in invoices:
            dir_path = Path.cwd() / "media" / invoice.trip_id
            dir_path.mkdir(parents=True, exist_ok=True)
            download_url = invoice.download_url

            filename = urlparse(download_url).path.split("/")[-1]
            download_path = dir_path / filename

            batch.append((invoice, download_path))

        await download_batch(batch)

        session.commit()


async def download_new_invoices(trip_ids: list[str]):
    await download_invoices(Invoice.trip_id.in_(trip_ids))


async def download_old_invoices():
    await download_invoices(Invoice.downloaded.is_(False))


if __name__ == "__main__":
    init_engine()
    asyncio.run(download_old_invoices())
