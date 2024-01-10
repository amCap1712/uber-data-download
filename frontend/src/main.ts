import { fetchAllTrips, fetchCompleteTripData } from "./uber-api.ts";
import {
  getSubmittedTrips,
  getUserUUID,
  recordSubmittedTrips,
} from "./storage.ts";
import { submitTrips } from "./collection-api.ts";
import { chunk } from "lodash-es";

const SUBMISSION_CHUNK_SIZE = 10;

async function downloadAndExportUberData() {
  const allTrips = await fetchAllTrips();
  const submittedTripIds = await getSubmittedTrips();

  const tripsToSubmit = [];
  for (const trip of allTrips) {
    if (!submittedTripIds.includes(trip.uuid)) {
      tripsToSubmit.push(trip);
    }
  }

  const promises = allTrips.map(async (trip: Trip) =>
    fetchCompleteTripData(trip),
  );
  const tripsData = await Promise.all(promises);

  const user_id = await getUserUUID();
  const chunks = chunk(tripsData, SUBMISSION_CHUNK_SIZE);
  for (const chunk of chunks) {
    const submittedTripIds = await submitTrips(user_id, chunk);
    await recordSubmittedTrips(submittedTripIds);
  }
}

downloadAndExportUberData();
