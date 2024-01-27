import { fetchWithRetry } from "./utils.ts";

const DATA_COLLECTION_API_URL = "https://kiran-research2.comminfo.rutgers.edu//uber-data-download/";

async function submitTrips(
  user_id: string,
  trips: TripCompleteDetails[],
): Promise<string[]> {
  const response = await fetchWithRetry(DATA_COLLECTION_API_URL, {
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
    body: JSON.stringify({
      user_id,
      data: trips,
    }),
  });
  if (response.ok) {
    return trips.map((trip) => trip.summary.uuid);
  } else {
    return [];
  }
}

export { submitTrips };
