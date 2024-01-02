const UBER_API_URL = "https://riders.uber.com/graphql";
const USER_UUID_KEY = "user-uuid";
const SUBMITTED_TRIPS_KEY = "submitted-trips";
const DATA_COLLECTION_API_URL = "http://127.0.0.1:8000/";

async function getUserUUID() {
    const data = await chrome.storage.local.get([USER_UUID_KEY]);
    const existingUserUUID = data[USER_UUID_KEY];
    if (existingUserUUID) {
        return existingUserUUID;
    }
    const newUserUUID = window.crypto.randomUUID();
    await chrome.storage.local.set({ USER_UUID_KEY: newUserUUID });
    return newUserUUID;
}

async function recordSubmittedTrips(trips) {
    const data = await chrome.storage.local.get([SUBMITTED_TRIPS_KEY]);
    const submittedTrips = data[SUBMITTED_TRIPS_KEY] ?? [];
    for (const trip of trips) {
        if (!submittedTrips.includes(trip)) {
            submittedTrips.push(trip);
        }
    }
    await chrome.storage.local.set({ SUBMITTED_TRIPS_KEY: submittedTrips });
}

async function callAPI(operationName, query, variables) {
    const body = {
        operationName,
        query,
        variables
    };
    const response = await fetch(UBER_API_URL, {
        "headers": {
            "content-type": "application/json",
            "x-csrf-token": "x",
        },
        "body": JSON.stringify(body),
        "method": "POST",
    });
    const text = await response.text();
    return JSON.parse(text);
}

async function fetchTrips(nextPageToken) {
    const query = `
query Activities(
  $cityID: Int
  $includePast: Boolean = true
  $includeUpcoming: Boolean = true
  $limit: Int = 5
  $nextPageToken: String
) {
  activities(cityID: $cityID) {
    cityID
    past(limit: $limit, nextPageToken: $nextPageToken)
      @include(if: $includePast) {
      activities {
        ...RVWebCommonActivityFragment
        __typename
      }
      nextPageToken
      __typename
    }
    upcoming @include(if: $includeUpcoming) {
      activities {
        ...RVWebCommonActivityFragment
        __typename
      }
      __typename
    }
    __typename
  }
}

fragment RVWebCommonActivityFragment on RVWebCommonActivity {
  buttons {
    isDefault
    startEnhancerIcon
    text
    url
    __typename
  }
  cardURL
  description
  imageURL {
    light
    dark
    __typename
  }
  subtitle
  title
  uuid
  __typename
}
`;
    const variables = {
        "includePast": true,
        "limit": 50
    };
    if (nextPageToken) {
        variables["nextPageToken"] = nextPageToken;
    }
    const json = await callAPI("Activities", query, variables);
    return json["data"]["activities"]["past"];
}

async function fetchTripInvoices(tripUUID) {
    const query = `
query GetInvoiceFiles($tripUUID: ID!) {
  invoiceFiles(tripUUID: $tripUUID) {
    archiveURL
    files {
      downloadURL
      __typename
    }
    __typename
  }
}
`;
    const variables = { tripUUID };
    const json = await callAPI("GetInvoiceFiles", query, variables);
    return json["data"]["invoiceFiles"]["files"];
}

async function fetchTripDetails(tripUUID) {
    const query = `
query GetTrip($tripUUID: String!) {
  getTrip(tripUUID: $tripUUID) {
    trip {
      beginTripTime
      cityID
      countryID
      disableCanceling
      disableRating
      driver
      dropoffTime
      fare
      guest
      isRidepoolTrip
      isScheduledRide
      isSurgeTrip
      isUberReserve
      jobUUID
      marketplace
      paymentProfileUUID
      status
      uuid
      vehicleDisplayName
      vehicleViewID
      waypoints
      __typename
    }
    mapURL
    polandTaxiLicense
    rating
    receipt {
      carYear
      distance
      distanceLabel
      duration
      vehicleType
      __typename
    }
    __typename
  }
}    
`;
    const variables = { tripUUID };
    const json = await callAPI("GetTrip", query, variables);
    return json["data"]["getTrip"];
}

async function fetchCompleteTripData(trip) {
    const tripUUID = trip["uuid"];
    const promises = await Promise.all([fetchTripDetails(tripUUID), fetchTripInvoices(tripUUID)]);
    return {
        summary: trip,
        details: promises[0],
        invoices: promises[1]
    };
}

async function fetchAllTrips() {
    let nextPageToken = null;
    const allTrips = [];
    do {
        const response = await fetchTrips(nextPageToken);
        allTrips.push(...response["activities"]);
        nextPageToken = response["nextPageToken"];
    } while (Boolean(nextPageToken));
    return allTrips;
}

async function submitTrips(trips) {
    const promises = trips.map(async trip => fetchCompleteTripData(trip));
    const tripsData = await Promise.all(promises);
    const chunks = chunkArray(tripsData, 10);

    const user_id = await getUserUUID();
    for (const chunk of chunks) {
        const response = await fetch(DATA_COLLECTION_API_URL, {
            headers: {
                "Content-Type": "application/json"
            },
            method: "POST",
            body: JSON.stringify({
                user_id,
                data: chunk
            })
        });
        if (response.ok) {
            const tripUUIDs = chunk.map(trip => trip["summary"]["uuid"]);
            await recordSubmittedTrips(tripUUIDs);
        }
    }
}

function chunkArray(array, size) {
    const chunks = [];
    for (let i = 0; i < array.length; i += size) {
        chunks.push(array.slice(i, i + size));
    }
    return chunks;
}

async function downloadAndExportUberData() {
    const allTrips = await fetchAllTrips();

    const data = await chrome.storage.local.get([SUBMITTED_TRIPS_KEY]);
    const submittedTripIds = data[SUBMITTED_TRIPS_KEY] ?? [];

    const tripsToSubmit = [];
    for (const trip of allTrips) {
        if (!submittedTripIds.includes(trip["uuid"])) {
            tripsToSubmit.push(trip);
        }
    }

    await submitTrips(tripsToSubmit);
}

downloadAndExportUberData();
