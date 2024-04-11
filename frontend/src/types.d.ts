type Trip = {
  uuid: string;
};

type TripCompleteDetails = {
  summary: Trip;
  details: never;
  invoices: never;
};
