import React, { Fragment } from "react";

import { useSearchParams } from "next/navigation";
import Link from "next/link";

import { GrHome, GrFolder, GrDocument } from "react-icons/gr";
import useS3Listing from "../../hooks/useS3Listing";

export default function S3Explorer() {
  const searchParams = useSearchParams();

  const prefix = sanitizePrefix(searchParams.get("prefix") || "");

  return (
    <div>
      <Navigation prefix={prefix} />
      <Listing prefix={prefix} />
    </div>
  );
}

function Navigation({ prefix }: { prefix: string }) {
  const folders = prefix
    .split("/")
    .slice(0, -1)
    .map((item, index, items) => ({
      name: `${item}/`,
      url: `/recordings/?prefix=${items.slice(0, index + 1).join("/")}/`,
      isCurrent: index === items.length - 1,
    }));

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        margin: "20px 0px",
      }}
    >
      <div>
        {folders.length === 0 ? (
          <div>
            <GrHome />
          </div>
        ) : (
          <div>
            <Link href="/recordings">
              <GrHome />
            </Link>
          </div>
        )}
      </div>

      {folders.map((item) => (
        <Fragment key={item.url}>
          &nbsp;&nbsp;&gt; &nbsp;&nbsp;
          <div>
            {item.isCurrent ? (
              <div style={{ fontWeight: "bold" }}>{item.name}</div>
            ) : (
              <div>
                <Link href={item.url}>{item.name}</Link>
              </div>
            )}
          </div>
        </Fragment>
      ))}
    </div>
  );
}

function Listing({ prefix }: { prefix: string }) {
  const {
    data,
    status,
    error,
  }: {
    data: { folders: any[]; objects: any[] } | null;
    status: string | null;
    error: Error | null;
  } = useS3Listing(prefix);

  return (
    <div>
      <table
        style={{
          borderSpacing: "30px 2px",
          borderCollapse: "separate",
          width: "100%",
        }}
      >
        <thead>
          <tr
            style={{
              fontWeight: "bold",
              textAlign: "left",
            }}
          >
            <th>Name</th>
            <th>Modified</th>
            <th>Size</th>
          </tr>
        </thead>
        <tbody>
          {(() => {
            switch (status) {
              case "loading":
                return (
                  <tr>
                    <td
                      style={{
                        padding: 30,
                        fontWeight: "bold",
                        color: "coral",
                      }}
                    >
                      Loading...
                    </td>
                  </tr>
                );
              case "error":
                return (
                  <tr>
                    <td>Failed to fetch data: {error?.message}</td>
                  </tr>
                );
              case "success":
                return (
                  <>
                    {data?.folders.map((item) => (
                      <tr key={item.path}>
                        <td>
                          <GrFolder />
                          &nbsp;
                          <Link href={item.url}>{item.name}</Link>
                        </td>
                        <td>-</td>
                        <td>-</td>
                      </tr>
                    ))}
                    {data?.objects.map((item) => (
                      <tr key={item.path}>
                        <td>
                          <GrDocument />
                          &nbsp;
                          <Link
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {item.name}
                          </Link>
                        </td>
                        <td>{new Date(item.lastModified).toLocaleString()}</td>
                        <td>{formatFileSize(item.size)}</td>
                      </tr>
                    ))}
                  </>
                );
            }
          })()}
        </tbody>
      </table>
    </div>
  );
}

export const sanitizePrefix = (prefix: string) =>
  prefix
    .trim()
    .replace(/\/+/g, "/")
    .replace(/(.*?)\/?$/, "$1/")
    .replace(/^\//, "");

export const formatFileSize = (size: number, digits = 2) => {
  if (size == 0) return "0 B";
  const units: string[] = ["B", "KB", "MB", "GB", "TB", "PB"];
  const exp: number = Math.floor(Math.log(size) / Math.log(1024));
  const converted = size / Math.pow(1024, exp);
  return `${converted.toFixed(digits)} ${units[exp]}`;
};
