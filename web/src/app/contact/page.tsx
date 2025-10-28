import Header from "../../components/Header";
import { Card } from "@/components/ui/card";

export default function Contact() {
  return (
    <div className="flex flex-col items-center justify-center">
      <Header />

      <div className="wireframe-bg"></div>

      <main className="relative z-10 flex flex-col items-center justify-center h-screen">
        <Card>
          <iframe 
            src="https://docs.google.com/forms/d/e/1FAIpQLSduVzouT2-1FGfuQSuQp9IKymfPvfwZDLnVt5yxo5zLm70Kig/viewform?embedded=true" 
            className="w-full h-[700px] border-0 bg-transparent min-w-[50vw] rounded-lg"
            title="Contact Form"
          >
            Loading…
          </iframe>
        </Card>
      </main>
    </div>
  );
}