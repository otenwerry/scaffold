import Header from "../../components/Header";

export default function Contact() {
  return (
    <div className="flex flex-col items-center justify-center">
      <Header />

      <div className="wireframe-bg"></div>

      <main className="relative z-10 flex flex-col items-center justify-center h-screen">
        <div className="overflow-visible rounded-lg relative w-full">
          <iframe 
            src="https://docs.google.com/forms/d/e/1FAIpQLSduVzouT2-1FGfuQSuQp9IKymfPvfwZDLnVt5yxo5zLm70Kig/viewform?embedded=true" 
            className="w-full h-[700px] border-0 bg-white/80 min-w-[50vw] rounded-lg md:pt-5"
            title="Contact Form"
          >
            Loading…
          </iframe>
        </div>
      </main>
    </div>
  );
}