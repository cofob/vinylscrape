import { ImageResponse } from "next/og";

export const size = {
  width: 180,
  height: 180,
};

export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          alignItems: "center",
          background: "linear-gradient(135deg, #f59e0b, #b45309)",
          color: "white",
          display: "flex",
          fontSize: 70,
          fontWeight: 700,
          height: "100%",
          justifyContent: "center",
          letterSpacing: -3,
          width: "100%",
        }}
      >
        VS
      </div>
    ),
    size,
  );
}
