"use client";

import { Suspense } from "react";

import Header from "../components/Header";
import Footer from "../components/Footer";

import S3Explorer from "../components/S3Browser";

import styles from "./page.module.scss";

export default function Recordings() {
  return (
    <div className={styles.page}>
      <Header />

      <div className="main-content">
        <main className={styles.main}>
          <article
            className="card-article"
            style={{ backgroundColor: "#f3e5f5" }}
          >
            <h3 className="card-heading-1">Recordings & Transcripts</h3>

            <div className="card-text">
              <Suspense>
                <S3Explorer />
              </Suspense>
            </div>
          </article>
        </main>
      </div>

      <Footer />
    </div>
  );
}
