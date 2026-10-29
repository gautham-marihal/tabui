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
            <h3 className="card-heading-1">Australian Bank HR MX Bot</h3>

            <div className="card-text">
              The objective of this demo is to showcase a voice-enabled virtual
              assistant, designed for an Australian Bank. The assistant is
              capable of answering HR-related questions by retrieving
              information from a generic Australian Bank HR Policy Manual
              prepared solely for demo purposes.
            </div>

            <h3 className="card-heading-3">Common Use cases:</h3>

            <div>
              <ul className="card-text">
                {questions.map((element: { id: number; question: string }) => (
                  <li key={element?.id}>{element.question}</li>
                ))}
              </ul>
            </div>
          </article>

          <TABWidget
            agentId="ausbank"
            livekitURL={process.env["NEXT_PUBLIC_AUSBANK_LIVEKIT_URL"] || ""}
            chatTextDisplayFilterEnabled={false}
          />
        </main>
      </div>

      <Footer />
    </div>
  );
}

const questions = [
  {
    id: 100,
    question:
      "How many weeks of paid parental leave do I get at Australian Bank?",
  },
  {
    id: 200,
    question:
      "Can I apply for flexible working hours if I have childcare responsibilities?",
  },
  {
    id: 300,
    question: "How do I apply for annual leave, and who approves it?",
  },
  {
    id: 400,
    question: "What happens if I need to take a personal or carer’s leave?",
  },

  {
    id: 500,
    question: "Am I eligible for long service leave, and when can I take it?",
  },

  {
    id: 600,
    question:
      "How does the grievance process work if I feel I’ve been treated unfairly?",
  },

  {
    id: 700,
    question: "What benefits do I get apart from salary?",
  },

  {
    id: 800,
    question: "Is there a policy on using social media during work hours?",
  },

  {
    id: 900,
    question:
      "What should I do when I resign—how do I return equipment and get my final pay?",
  },
];
