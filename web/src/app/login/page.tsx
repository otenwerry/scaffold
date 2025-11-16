import Header from "../../components/Header";
import Footer from "../../components/Footer";
import { Card, CardTitle, CardContent } from "@/components/ui/card";
import Link from "next/link";

export default function LogIn() {
  return (
    <div className="flex flex-col items-center justify-center">
      <Header />

      <div className="wireframe-bg"></div>

      <main className="relative z-10 flex flex-col items-center justify-start min-h-screen px-4 pt-20 md:pt-25">
        <Card>
          <CardTitle className="text-4xl font-bold text-gray-900 leading-relaxed text-center">Log In</CardTitle>
          <CardContent className="text-lg md:text-lg text-gray-800 max-w-3xl mx-auto leading-relaxed text-left">
          <strong>Lorum ipsum</strong> dolor sit amet
          </CardContent>
        </Card>
        <Footer />
      </main>
    </div>
  );
}