import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';
import './index.css';
import 'bootstrap/dist/css/bootstrap.min.css';

const root = document.getElementById("root")!;
const app = document.createElement("div");
root.appendChild(app);

ReactDOM.createRoot(app).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
