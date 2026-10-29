import React from "react";

import ClerkAuth from "../components/ClerkAuth";

import Header from "../components/Header";
import Footer from "../components/Footer";

import styles from "./page.module.scss";

export default function TabDemo() {
  return (
    <div className={styles.page}>
      <Header />

      <div className="main-content">
        <main className={styles.main}>
          <article className="card-article">
            <h3 className="card-heading-1"></h3>

            <div style={{ height: 200, display: "grid", placeItems: "center" }}>
              <ClerkAuth />
            </div>
          </article>
        </main>
      </div>

      <Footer />
    </div>
  );
}
