"use client";

import React from "react";

import { Tab, Tabs, TabList, TabPanel } from "react-tabs";

import TABWidget from "../components/TABWidget";

import Header from "../components/Header";
import Footer from "../components/Footer";

import RAG from "../components/self-care-bank/RAG";
import Customers from "../components/self-care-bank/Customers";

import styles from "./page.module.scss";

import "react-tabs/style/react-tabs.css";

export default function TabDemo() {
  return (
    <div className={styles.page} id="customers">
      <Header />

      <div className="main-content">
        <main className={styles.main}>
          <article
            className="card-article"
            style={{ backgroundColor: "#f3e5f5" }}
          >
            <h3 className="card-heading-1">Self-Care Bank MX Bot</h3>

            <div className="card-text">
              <Tabs>
                <TabList>
                  <Tab className="custom-tab">Bot Details</Tab>
                  <Tab className="custom-tab">Customer Data</Tab>
                  <Tab className="custom-tab">Bank Data</Tab>
                </TabList>

                <TabPanel>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr",
                      gridGap: 20,
                    }}
                  >
                    <div>
                      Self-Care Bank&apos;s AI multi-modal bot is your 24/7
                      financial assistant, designed to make banking seamless and
                      intuitive. It combines text, voice, and image recognition
                      to assist with tasks like checking balances, transferring
                      funds, or analyzing transactions. With advanced eKYC
                      capabilities, the bot simplifies account opening by
                      securely verifying your identity through documents you can
                      either upload digitally or show to the camera during the
                      verification process.
                    </div>

                    <div>
                      <img
                        alt="Jaka Bank"
                        src="https://dicepoc.tetherfi.cloud/cdn/tmac/bankjakaweb.png"
                        style={{
                          width: "80%",
                          objectFit: "cover",
                        }}
                      />
                    </div>
                  </div>
                </TabPanel>

                <TabPanel>
                  <div>
                    <Customers />
                  </div>
                </TabPanel>

                <TabPanel>
                  <RAG />
                </TabPanel>
              </Tabs>
            </div>
          </article>

          <TABWidget
            agentId="selfcarebank"
            livekitURL={
              process.env["NEXT_PUBLIC_SELFCAREBANK_LIVEKIT_URL"] || ""
            }
            chatTextDisplayFilterEnabled={true}
          />
        </main>
      </div>

      <Footer />
    </div>
  );
}
