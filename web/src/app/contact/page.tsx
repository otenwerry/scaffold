import Header from "../../components/Header";

export default function Contact() {
  return (
    <div className="flex flex-col items-center justify-center">
      <Header />

      <div className="wireframe-bg"></div>

      <main className="relative z-10 flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] px-4">
        <div className="max-w-4xl mx-auto background-white max-h-[800px]">
          <iframe src="https://docs.google.com/forms/d/e/1FAIpQLSduVzouT2-1FGfuQSuQp9IKymfPvfwZDLnVt5yxo5zLm70Kig/viewform?embedded=true" width={800} height={700} frameBorder="0" title="Contact Form" style={{ background: "white" }}>Loading…</iframe>
        </div>
      </main>

    </div>
  );
}