import React from "react";
import axios from "axios";
import { MarkdownHooks } from "react-markdown";

const RAG: React.FC = () => {
  const [loading, setLoading] = React.useState(false);
  const [data, setData] = React.useState("");
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    setLoading(true);
    setError(null);
    setData("");

    axios
      .get(
        `${process.env.NEXT_PUBLIC_SCBANK_DATA_API}/self-care-bank-docs/RAG.md`
      )
      .then((response) => {
        setData(response?.data);
      })
      .catch((error) => {
        setError(error?.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  return (
    <div style={{ minHeight: 300, display: "grid", placeItems: "center" }}>
      {loading ? (
        <div style={{ color: "green" }}>Loading...</div>
      ) : error ? (
        <div style={{ color: "orangered" }}>{error}</div>
      ) : (
        <div className="markdown-content">
          <MarkdownHooks>{data}</MarkdownHooks>
        </div>
      )}
    </div>
  );
};

export default RAG;

const markdown = "# Hi, *Pluto*!";
