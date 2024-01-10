import { fetchWithRetry } from "./utils.ts";

const UBER_API_URL = "https://riders.uber.com/graphql";

async function callAPI(operationName: string, query: string, variables: any) {
  const body = {
    operationName,
    query,
    variables,
  };
  const response = await fetchWithRetry(UBER_API_URL, {
    headers: {
      "content-type": "application/json",
      "x-csrf-token": "x",
    },
    body: JSON.stringify(body),
    method: "POST",
  });
  const text = await response.text();
  return JSON.parse(text);
}

async function fetchTripsPage(nextPageToken: string | null) {
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
  const variables: any = {
    includePast: true,
    limit: 50,
  };
  if (nextPageToken) {
    variables["nextPageToken"] = nextPageToken;
  }
  const json = await callAPI("Activities", query, variables);
  return json["data"]["activities"]["past"];
}

async function fetchTripInvoices(tripUUID: string) {
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

async function fetchTripDetails(tripUUID: string) {
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

async function fetchCompleteTripData(trip: Trip) {
  const tripUUID = trip.uuid;
  const promises = await Promise.all([
    fetchTripDetails(tripUUID),
    fetchTripInvoices(tripUUID),
  ]);
  return {
    summary: trip,
    details: promises[0],
    invoices: promises[1],
  };
}

async function fetchAllTrips() {
  let nextPageToken = null;
  const allTrips = [];
  do {
    const response = await fetchTripsPage(nextPageToken);
    allTrips.push(...response["activities"]);
    nextPageToken = response["nextPageToken"];
  } while (Boolean(nextPageToken));
  return allTrips;
}

export {
  fetchAllTrips,
  fetchCompleteTripData,
  fetchTripDetails,
  fetchTripInvoices,
};
