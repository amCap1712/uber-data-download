import { fetchWithRetry } from './utils.ts';
import { transferReceipt } from './collection-api.ts';

const UBER_API_URL = 'https://riders.uber.com/graphql';

type TripsVariables = {
  includePast: boolean;
  includeUpcoming: boolean;
  orderTypes: Array<string>;
  profileType: string;
  cityID?: number;
  limit: number;
  nextPageToken?: string;
};

async function callAPI(operationName: string, query: string, variables: unknown) {
  const body = {
    operationName,
    query,
    variables,
  };
  const response = await fetchWithRetry(UBER_API_URL, {
    headers: {
      'content-type': 'application/json',
      'x-csrf-token': 'x',
    },
    body: JSON.stringify(body),
    method: 'POST',
  });
  const text = await response.text();
  return JSON.parse(text);
}

async function fetchTripsPage(cityID: number | null, nextPageToken: string | null) {
  const query = `
query Activities($cityID: Int, $endTimeMs: Float, $includePast: Boolean = true, $includeUpcoming: Boolean = true, $limit: Int = 5, $nextPageToken: String, $orderTypes: [RVWebCommonActivityOrderType\u0021] = [RIDES, TRAVEL], $profileType: RVWebCommonActivityProfileType = PERSONAL, $startTimeMs: Float) {
  activities(cityID: $cityID) {
    cityID
    past(
      endTimeMs: $endTimeMs
      limit: $limit
      nextPageToken: $nextPageToken
      orderTypes: $orderTypes
      profileType: $profileType
      startTimeMs: $startTimeMs
    ) @include(if: $includePast) {
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
  const variables: TripsVariables = {
    includePast: true,
    includeUpcoming: false,
    orderTypes: ['RIDES', 'TRAVEL'],
    profileType: 'PERSONAL',
    limit: 10,
  };
  if (nextPageToken) {
    variables['nextPageToken'] = nextPageToken;
  }
  if (cityID) {
    variables['cityID'] = cityID;
  }
  const json = await callAPI('Activities', query, variables);
  return json['data']['activities'];
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
  const json = await callAPI('GetInvoiceFiles', query, variables);
  return json['data']['invoiceFiles']['files'];
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
  const json = await callAPI('GetTrip', query, variables);
  return json['data']['getTrip'];
}

async function fetchCompleteTripData(trip: Trip) {
  const tripUUID = trip.uuid;
  const promises = await Promise.all([
    fetchTripDetails(tripUUID),
    fetchTripInvoices(tripUUID),
    transferReceipt(tripUUID),
  ]);
  return {
    summary: trip,
    details: promises[0] as never,
    invoices: promises[1] as never,
  };
}

async function fetchAllTrips() {
  let nextPageToken = null;
  let cityID = null;
  const allTrips = [];
  do {
    const response = await fetchTripsPage(cityID, nextPageToken);
    allTrips.push(...response['past']['activities']);
    nextPageToken = response['past']['nextPageToken'];
    cityID = response['cityID'];
  } while (nextPageToken);
  return allTrips;
}

export { fetchAllTrips, fetchCompleteTripData, fetchTripDetails, fetchTripInvoices };
