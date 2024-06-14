import { useCallback, useState } from 'react';
import './App.css';
import Modal from 'react-bootstrap/Modal';
import { fetchAllTrips, fetchCompleteTripData } from './uber-api.ts';
import { chunk } from 'lodash-es';
import { submitTrips } from './collection-api.ts';
import ProgressBar from 'react-bootstrap/ProgressBar';
import Button from 'react-bootstrap/Button';

const SUBMISSION_CHUNK_SIZE = 10;
const STUDY_THANKS_URL = 'https://kiran-research2.comminfo.rutgers.edu/uber-data-download/study/thanks';

function App() {
  const [disabled, setDisabled] = useState(false);
  const [showModal, setShowModal] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [showComplete, setShowComplete] = useState(false);

  const handleClick = useCallback(() => {
    async function downloadAndExportUberData() {
      setDisabled(false);
      setMessage('Downloading trips data from Uber...');
      const allTrips = await fetchAllTrips();

      if (allTrips.length === 0) {
        setMessage('No trips found.');
      }

      setMessage('Gathering trip invoices from Uber...');
      const promises = allTrips.map(async (trip: Trip) => fetchCompleteTripData(trip));
      const tripsData = await Promise.all(promises);

      const chunks = chunk(tripsData, SUBMISSION_CHUNK_SIZE);
      for (const [idx, chunk] of chunks.entries()) {
        setMessage(`Submitting trip invoices for research (${idx * SUBMISSION_CHUNK_SIZE} / ${tripsData.length})...`);
        const uuid = crypto.randomUUID();
        await submitTrips(uuid, chunk);
      }
      setMessage('Done.');
      setShowComplete(true);
    }
    downloadAndExportUberData();
  }, []);

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
                  <Button href={STUDY_THANKS_URL}>Click here to complete the study</Button>
                </div>
              ) : message ? (
                <div>
                  <p>{message}</p>
                  <ProgressBar animated striped variant="info" now={100} />
                </div>
              ) : (
                <Button disabled={disabled} onClick={handleClick}>
                  Start data export
                </Button>
              )}
            </Modal.Body>
          </Modal.Dialog>
        </div>
      )}
    </>
  );
}

export default App;
