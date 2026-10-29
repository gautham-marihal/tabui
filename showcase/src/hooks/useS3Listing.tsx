import React from "react";

const useS3Listing = (prefix: string) => {
  const [data, setData] = React.useState<{
    folders: any[];
    objects: any[];
  } | null>({ folders: [], objects: [] });
  const [error, setError] = React.useState<Error | null>(null);
  const [status, setStatus] = React.useState<string | null>(null);

  React.useEffect(() => {
    setStatus("loading");
    fetchS3Files(prefix)
      .then((s3Data) => {
        setData(s3Data);
        setStatus("success");
      })
      .catch((e) => {
        setError(e);
        setStatus("error");
      });
  }, [prefix]);

  return { data, status, error };
};

const fetchS3Files = async (prefix: string) => {
  const response = await fetch("/api/s3?prefix=" + prefix);
  const body = await response.json().catch(() => null);

  // an answer that is not a listing (S3 not set up, or a failure) is shown as an error, not read as one
  if (!response.ok || !Array.isArray(body?.folders) || !Array.isArray(body?.objects)) {
    throw new Error(body?.error || `The recordings could not be listed (HTTP ${response.status}).`);
  }
  return body;
};

export default useS3Listing;
