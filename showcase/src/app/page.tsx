import Footer from "./components/Footer";
import Header from "./components/Header";

import styles from "./page.module.scss";

export default function Home() {
  return (
    <div className={styles.page}>
      <Header />

      <div className="main-content">
        <main className={styles.main} style={{ marginBottom: 60 }}>
          <section className="hero-banner">
            <div style={{ maxWidth: 500 }}>
              <h2 style={{ textAlign: "center", fontSize: 30 }}>
                MX Bots by Tetherfi
              </h2>

              <h3
                style={{
                  textAlign: "center",
                  fontSize: 20,
                  marginTop: 20,
                  lineHeight: 1.4,
                }}
              >
                Revolutionizing customer engagement with AI-driven
                conversational intelligence that speaks your customer&apos;s
                language
              </h3>
            </div>
          </section>

          <section className="cards-section">
            <article
              className="card-article"
              style={{ backgroundColor: "#e0f2f1" }}
            >
              <h3 className="card-heading-1">What is Tetherfi MX Bot?</h3>

              <div className="card-text">
                Tetherfi MX Bot is a real-time, AI-powered Multi-Modal
                automation solution designed for modern, high-volume contact
                centers. Genuinely Multi-Modal that can handle customer input in
                voice, video, text, and file data. Blending advanced
                Speech-to-Text (STT), AI LLM, Text-to-Speech (TTS), and
                enterprise-grade backend integration, it enables self-service
                and seamless handoffs to live agents with full context,
                transcription, and Smart Assist capabilities. Whether it is
                answering routine queries, verifying identity, or escalating
                with real-time insight, Tetherfi MX Bot helps organizations
                scale CX while reducing operational load.
              </div>

              <h3 className="card-heading-3">Common Use cases:</h3>

              <div>
                <ul className="card-text">
                  <li>Customer FAQs and support queries</li>
                  <li>Appointment scheduling and order tracking</li>
                  <li>Password resets and basic account support</li>
                  <li>Outage notification and confirmations</li>
                </ul>
              </div>
            </article>

            <article
              className="card-article"
              style={{ backgroundColor: "#fce4ec" }}
            >
              <h3 className="card-heading-1">Key Features</h3>

              <div>
                <ul>
                  <li>
                    <div className="card-heading-2">
                      Real-Time Speech-to-Text (STT)
                    </div>
                    <div className="card-text">
                      High-accuracy transcription powered by OpenAI Whisper and
                      custom STT models.
                    </div>
                  </li>

                  <li>
                    <div className="card-heading-2">
                      Intent Detection &amp; Tagging
                    </div>
                    <div className="card-text">
                      AI-driven interpretation of customer intent with
                      customizable enterprise guardrails.
                    </div>
                  </li>

                  <li>
                    <div className="card-heading-2">
                      Self-Service Flows with Host Integration
                    </div>
                    <div className="card-text">
                      Enable secure balance checks, authentication,
                      recontracting, and more via REST, screen scraping, or DB
                      connections.
                    </div>
                  </li>

                  <li>
                    <div className="card-heading-2">
                      LLM + Structured Bot Blending
                    </div>
                    <div className="card-text">
                      Combine open AI responses with rule-based forms to handle
                      sensitive customer information securely on-prem
                    </div>
                  </li>

                  <li>
                    <div className="card-heading-2">Mult-Modal User Input</div>
                    <div className="card-text">
                      Enhanced enterprise customer engagement through handling
                      of voice, video, text, and file data.
                    </div>
                  </li>
                </ul>
              </div>
            </article>

            <article
              className="card-article"
              style={{ backgroundColor: "#e8f5e9" }}
            >
              <h3 className="card-heading-1">Key Features</h3>

              <div>
                <ul>
                  <li>
                    <div className="card-heading-2">
                      Customized agent accents & personas
                    </div>
                    <div className="card-text">
                      Function effectively in noisy environments, support
                      interruptions by caller, and offer customized accents and
                      agent personas for a tailored experience.
                    </div>
                  </li>

                  <li>
                    <div className="card-heading-2">
                      Smart Assist for Agents
                    </div>
                    <div className="card-text">
                      Auto-transcription, call summaries, sentiment detection,
                      and suggested responses-right in the agent desktop.
                    </div>
                  </li>

                  <li>
                    <div className="card-heading-2">
                      Multilingual + Translation
                    </div>
                    <div className="card-text">
                      Supports regional languages with real-time English
                      translation.
                    </div>
                  </li>

                  <li>
                    <div className="card-heading-2">
                      Voice Clip Upload & Playback
                    </div>
                    <div className="card-text">
                      Process inbound voice files for transcription and summary.
                    </div>
                  </li>

                  <li>
                    <div className="card-heading-2">
                      Visual Flow Designer (Low/No Code)
                    </div>
                    <div className="card-text">
                      Drag-and-drop interface for building, updating, and
                      deploying conversational flows across IVR, MX Bot, and
                      chat.
                    </div>
                  </li>
                </ul>
              </div>
            </article>

            <article
              className="card-article"
              style={{ backgroundColor: "#f3e5f5" }}
            >
              <h3 className="card-heading-1">HOW IT WORKS</h3>

              <ul>
                <li>
                  <div className="card-heading-2">Call Initiation</div>
                  <div className="card-text">
                    Customer dials in via hotline, PSTN, Mobile App, or Website.
                  </div>
                </li>

                <li>
                  <div className="card-heading-2">Speech Recognition & STT</div>
                  <div className="card-text">
                    STT captures and transcribes audio into structured text.
                  </div>
                </li>

                <li>
                  <div className="card-heading-2">
                    Intent Processing & Response Generation
                  </div>
                  <div className="card-text">
                    Transcription flows through LLM, detecting intents and
                    generating responses based on context.
                  </div>
                </li>

                <li>
                  <div className="card-heading-2">
                    Bot Connector & Enterprise Integration
                  </div>
                  <div className="card-text">
                    Bot uses structured flows or LLM-based responses to address
                    queries or pass validated info to host systems.
                  </div>
                </li>

                <li>
                  <div className="card-heading-2">
                    Live Agent Handoff (if needed)
                  </div>
                  <div className="card-text">
                    Human Agents receive full context, transcription history,
                    and Smart Assist prompts.
                  </div>
                </li>
              </ul>
            </article>

            <article
              className="card-article"
              style={{ backgroundColor: "#e0f7fa" }}
            >
              <h3 className="card-heading-1">Built for Enterprises</h3>

              <div>
                <ul className="card-text">
                  <li>
                    Secure: All sensitive data resides on customer premises
                  </li>

                  <li>Scalable: Designed for high-call-volume environments</li>

                  <li>
                    Flexible: Integrates with Avaya, Genesys, Twilio, Cisco,
                    3CX, NICE, Salesforce, SharePoint & more
                  </li>

                  <li>
                    Compliant: Built with enterprise governance, caching, and
                    audit controls
                  </li>

                  <li>
                    Channel-Ready: Deploy across voice, chat, social, WhatsApp,
                    and web
                  </li>
                </ul>
              </div>
            </article>

            <article
              className="card-article"
              style={{ backgroundColor: "#ede7f6" }}
            >
              <h3 className="card-heading-1">Why Tetherfi MX Bots?</h3>

              <div>
                <ul className="card-text">
                  <li>Reduces agent workload by up to 40%</li>

                  <li>
                    Improves containment and CSAT via accurate intent mapping
                  </li>

                  <li>Empowers agents with real-time assist tools</li>

                  <li>
                    Accelerates digital transformation in regulated industries
                  </li>

                  <li>
                    Prebuilt integrations with Amazon Connect, Genesys, NICE,
                    etc.
                  </li>

                  <li>
                    Proven ROI: Faster responses, fewer live-agent tickets
                  </li>

                  <li>Completely GDPR / PCI DSS / ISO 27001 compliant</li>
                </ul>
              </div>
            </article>
          </section>
        </main>
      </div>

      <Footer />
    </div>
  );
}
