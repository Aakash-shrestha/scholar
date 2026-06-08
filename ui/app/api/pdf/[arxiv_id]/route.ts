import { NextRequest, NextResponse } from "next/server";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ arxiv_id: string }> },
) {
  const { arxiv_id } = await params;

  const res = await fetch(`https://arxiv.org/pdf/${arxiv_id}`);

  if (!res.ok) {
    return new NextResponse("PDF not found", { status: res.status });
  }

  return new NextResponse(res.body, {
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": "inline",
    },
  });
}
