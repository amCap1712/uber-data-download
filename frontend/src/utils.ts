import fetch_retry from "fetch-retry";

const fetchWithRetry = fetch_retry(window.fetch, {
  retries: 5,
  retryDelay: function (attempt) {
    return Math.pow(2, attempt) * 1000; // 1000, 2000, 4000
  },
  retryOn: function (attempt, error, response) {
    // retry on any network error, or 4xx or 5xx status codes
    if (error !== null || (response && response.status >= 400)) {
      console.log(`retrying, attempt number ${attempt + 1}`);
      return true;
    }
    return false;
  },
});

export { fetchWithRetry };
