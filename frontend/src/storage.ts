const USER_UUID_KEY = "user-uuid";
const SUBMITTED_TRIPS_KEY = "submitted-trips";

async function getUserUUID(): Promise<string> {
  const data = await chrome.storage.local.get([USER_UUID_KEY]);
  const existingUserUUID = data[USER_UUID_KEY];
  if (existingUserUUID) {
    return existingUserUUID;
  }
  const newUserUUID = window.crypto.randomUUID();
  await chrome.storage.local.set({ USER_UUID_KEY: newUserUUID });
  return newUserUUID;
}

async function getSubmittedTrips(): Promise<string[]> {
  const data = await chrome.storage.local.get([SUBMITTED_TRIPS_KEY]);
  return data[SUBMITTED_TRIPS_KEY] ?? [];
}

async function recordSubmittedTrips(trips: string[]) {
  const submittedTrips = await getSubmittedTrips();
  for (const trip of trips) {
    if (!submittedTrips.includes(trip)) {
      submittedTrips.push(trip);
    }
  }
  await chrome.storage.local.set({ SUBMITTED_TRIPS_KEY: submittedTrips });
}

export { getUserUUID, getSubmittedTrips, recordSubmittedTrips };
