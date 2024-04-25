import { fetchWithRetry } from './utils.ts';

const DATA_COLLECTION_API_URL = 'https://kiran-research2.comminfo.rutgers.edu/uber-data-download/';
const RECEIPT_COLLECTION_API_URL = `${DATA_COLLECTION_API_URL}/receipts`;

async function transferReceipt(tripUUID: string) {
  const response = await fetch(`https://riders.uber.com/trips/${tripUUID}/receipt?contentType=PDF`);
  if (response.status == 200) {
    const file = await response.blob();
    const formData = new FormData();
    formData.append('file', file);
    await fetch(RECEIPT_COLLECTION_API_URL + `?trip_id=${tripUUID}`, {
      method: 'POST',
      body: formData,
    });
  }
}

async function submitTrips(prolific_id: string, trips: TripCompleteDetails[]): Promise<string[]> {
  const response = await fetchWithRetry(DATA_COLLECTION_API_URL, {
    headers: {
      'Content-Type': 'application/json',
    },
    method: 'POST',
    body: JSON.stringify({
      user_id: prolific_id,
      data: trips,
    }),
  });
  if (response.ok) {
    return trips.map((trip) => trip.summary.uuid);
  } else {
    return [];
  }
}

export { transferReceipt, submitTrips };
