import {useCallback, useState} from 'react';
import './App.css';
import Modal from 'react-bootstrap/Modal';
import {fetchAllTrips, fetchCompleteTripData} from "./uber-api.ts";
import {getSubmittedTrips, getUserUUID, recordSubmittedTrips} from "./storage.ts";
import {chunk} from "lodash-es";
import {submitTrips} from "./collection-api.ts";
import ProgressBar from "react-bootstrap/ProgressBar";
import Button from "react-bootstrap/Button";

const SUBMISSION_CHUNK_SIZE = 10;

function App() {
    const [disabled, setDisabled] = useState(false);
    const [showModal, setShowModal] = useState(true);
    const [message, setMessage] = useState<string | null>(null);

    const handleClick = useCallback(() => {
        async function downloadAndExportUberData() {
            setDisabled(false);
            setMessage("Downloading trips data from Uber...");
            const allTrips = await fetchAllTrips();

            setMessage("Filtering already submitted trip ids...");
            const submittedTripIds = await getSubmittedTrips();

            const tripsToSubmit = [];
            for (const trip of allTrips) {
                if (!submittedTripIds.includes(trip.uuid)) {
                    tripsToSubmit.push(trip);
                }
            }

            setMessage("Gathering trip invoices from Uber...");
            const promises = allTrips.map(async (trip: Trip) =>
                fetchCompleteTripData(trip),
            );
            const tripsData = await Promise.all(promises);

            const user_id = await getUserUUID();
            const chunks = chunk(tripsData, SUBMISSION_CHUNK_SIZE);
            for (const [idx, chunk] of chunks.entries()) {
                setMessage(`Submitting trip invoices for research (${idx * SUBMISSION_CHUNK_SIZE} / ${tripsData.length})...`);
                const submittedTripIds = await submitTrips(user_id, chunk);
                await recordSubmittedTrips(submittedTripIds);
            }
            setMessage("Done.");
        }
        downloadAndExportUberData();

    }, []);

    return (
        <>
            {showModal &&
                <div
                    className="modal show"
                    style={{display: 'block'}}
                >
                    <Modal.Dialog>
                        <Modal.Header closeButton onHide={() => setShowModal(false)}>
                            <Modal.Title>Uber Data Export</Modal.Title>
                        </Modal.Header>
                        <Modal.Body>
                            {!message &&
                                <Button disabled={disabled} onClick={handleClick}>
                                    Start data export
                                </Button>
                            }
                            {message &&
                                <div>
                                    <p>{message}</p>
                                    <ProgressBar animated striped variant="info" now={100} />
                                </div>}
                        </Modal.Body>
                    </Modal.Dialog>
                </div>
            }
        </>
    )
}

export default App;
