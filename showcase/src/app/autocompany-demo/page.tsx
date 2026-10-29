import React from "react";

import Image from "next/image";

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
            <h3 className="card-heading-1">AutoZone - MX Bot</h3>

            <div>
              <img
                width="100%"
                alt="Autozone"
                src={"https://dice.tetherfi.cloud/cdn/livekit/autozone.png"}
              />
            </div>
          </article>

          <TABWidget
            agentId="autocompany"
            livekitURL={
              process.env["NEXT_PUBLIC_AUTOCOMPANY_LIVEKIT_URL"] || ""
            }
            chatTextDisplayFilterEnabled={false}
          />
        </main>
      </div>

      <Footer />
    </div>
  );
}
