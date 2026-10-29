"use client";

import useChatAndTranscription from "@/hooks/useChatAndTranscription";
// import { useLocalParticipant } from "@livekit/components-react";
import Image from "next/image";
import React, { useRef } from "react";

function ButtonUpload() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  // const { localParticipant } = useLocalParticipant();
  const { send } = useChatAndTranscription();

  const handleButtonClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      // const info = await localParticipant.sendFile(file, {
      //   mimeType: file.type,
      //   topic: "images",
      // });
      await send(file.name, { attachments: [file], topic: "image-upload" });
      console.log("Files uploaded:", files);
      // console.log(`Files sent with s tream ID: ${info.id}`);
    }
  };

  return (
    <div className="lk-button-group">
      <button
        onClick={handleButtonClick}
        className="lk-button"
        style={{
          borderRadius: "10px",
        }}
      >
        <Image
          src="/images/attachment.svg"
          alt="attachment"
          width={17}
          height={17}
        />
      </button>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        style={{ display: "none" }}
        onChange={handleFileSelect}
      />
    </div>
  );
}
export default ButtonUpload;
