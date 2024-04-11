import { useCallback, useState } from 'react';
import './App.css';
import Modal from 'react-bootstrap/Modal';
import { fetchAllTrips, fetchCompleteTripData } from './uber-api.ts';
import { getSubmittedTrips, recordSubmittedTrips } from './storage.ts';
import { chunk } from 'lodash-es';
import { submitTrips } from './collection-api.ts';
import ProgressBar from 'react-bootstrap/ProgressBar';
import Button from 'react-bootstrap/Button';
import { Form } from 'react-bootstrap';

const SUBMISSION_CHUNK_SIZE = 10;
const COMPLETION_URL = 'https://app.prolific.com/submissions/complete?cc=CHFVP5PM';

function App() {
  const [disabled, setDisabled] = useState(false);
  const [showModal, setShowModal] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [prolific_id, setProlificId] = useState<string>('');
  const [showExport, setShowExport] = useState(false);
  const [showComplete, setShowComplete] = useState(false);

  const handleClick = useCallback(() => {
    async function downloadAndExportUberData() {
      setDisabled(false);
      setMessage('Downloading trips data from Uber...');
      const allTrips = await fetchAllTrips();

      setMessage('Filtering already submitted trip ids...');
      const submittedTripIds = await getSubmittedTrips();

      const tripsToSubmit = [];
      for (const trip of allTrips) {
        if (!submittedTripIds.includes(trip.uuid)) {
          tripsToSubmit.push(trip);
        }
      }

      setMessage('Gathering trip invoices from Uber...');
      const promises = allTrips.map(async (trip: Trip) => fetchCompleteTripData(trip));
      const tripsData = await Promise.all(promises);

      const chunks = chunk(tripsData, SUBMISSION_CHUNK_SIZE);
      for (const [idx, chunk] of chunks.entries()) {
        setMessage(`Submitting trip invoices for research (${idx * SUBMISSION_CHUNK_SIZE} / ${tripsData.length})...`);
        const submittedTripIds = await submitTrips(prolific_id, chunk);
        await recordSubmittedTrips(submittedTripIds);
      }
      setMessage('Done.');
      setShowComplete(true);
    }

    downloadAndExportUberData();
  }, [prolific_id]);

  return (
    <>
      {showModal && (
        <div className="modal show" style={{ display: 'block' }}>
          <Modal.Dialog>
            <Modal.Header closeButton onHide={() => setShowModal(false)}>
              <Modal.Title>Uber Data Export</Modal.Title>
            </Modal.Header>
            <Modal.Body>
              {showComplete ? (
                <div>
                  <p>Thank you for participating in the study.</p>
                  <Button href={COMPLETION_URL}>Click here to complete the study</Button>
                </div>
              ) : showExport ? (
                message ? (
                  <div>
                    <p>{message}</p>
                    <ProgressBar animated striped variant="info" now={100} />
                  </div>
                ) : (
                  <Button disabled={disabled} onClick={handleClick}>
                    Start data export
                  </Button>
                )
              ) : (
                <div>
                  <Form.Label htmlFor="inputProlificId">Enter your Prolific Id here:</Form.Label>
                  <Form.Control
                    type="text"
                    id="inputProlificId"
                    onChange={(event) => {
                      setProlificId(event.target.value);
                    }}
                  />
                  <Button
                    style={{ padding: '8px' }}
                    onClick={() => {
                      setShowExport(true);
                    }}
                  >
                    Proceed
                  </Button>
                </div>
              )}
            </Modal.Body>
          </Modal.Dialog>
        </div>
      )}
    </>
  );
}

export default App;
