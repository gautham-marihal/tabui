import React from "react";

import TABWidget from "../components/TABWidget";

import Header from "../components/Header";
import Footer from "../components/Footer";

import styles from "./page.module.scss";

export default function TabDemo() {
  return (
    <div className={styles.page}>
      <Header />

      <div className="main-content">
        <main className={styles.main}>
          <article
            className="card-article"
            style={{ backgroundColor: "#f3e5f5" }}
          >
            <h3 className="card-heading-1">Sasha Health MX Bot</h3>

            <div className="card-text">Healthcare MX Bot</div>
          </article>

          <TABWidget
            agentId="singhealth"
            livekitURL={process.env["NEXT_PUBLIC_SINGHEALTH_LIVEKIT_URL"] || ""}
            chatTextDisplayFilterEnabled={true}
          />
        </main>
      </div>

      <Footer />
    </div>
  );
}
