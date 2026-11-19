import { redirect } from "next/navigation";

export default function RoomRedirect({ params }: { params: { room: string } }) {
  redirect(`/messages?room=${encodeURIComponent(params.room)}`);
}
