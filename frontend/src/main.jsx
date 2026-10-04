import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import { PlayerProvider } from "./player.jsx";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <PlayerProvider>
      <App />
    </PlayerProvider>
  </React.StrictMode>
);
