type P = { className?: string; size?: number };

function Svg({ size = 20, className, children, fill = "none" }: P & { children: React.ReactNode; fill?: string }) {
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke="currentColor"
      strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className={className}>
      {children}
    </svg>
  );
}

export const HomeIcon = (p: P) => <Svg {...p}><path d="M3 11l9-7 9 7" /><path d="M5 10v10h14V10" /><path d="M10 20v-6h4v6" /></Svg>;
export const BuildingIcon = (p: P) => <Svg {...p}><rect x="4" y="3" width="16" height="18" rx="1" /><path d="M9 7h1M14 7h1M9 11h1M14 11h1M10 21v-4h4v4" /></Svg>;
export const TruckIcon = (p: P) => <Svg {...p}><path d="M2 6h11v10H2zM13 10h4l4 3v3h-8" /><circle cx="6" cy="18" r="2" /><circle cx="17" cy="18" r="2" /></Svg>;
export const SofaIcon = (p: P) => <Svg {...p}><path d="M4 12V9a2 2 0 012-2h12a2 2 0 012 2v3" /><path d="M2 12h20v5H2zM5 17v3M19 17v3" /></Svg>;
export const SparkleIcon = (p: P) => <Svg {...p}><path d="M12 3l1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8z" /></Svg>;
export const SearchIcon = (p: P) => <Svg {...p}><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></Svg>;
export const ChatIcon = (p: P) => <Svg {...p}><path d="M4 5h16v11H9l-5 4z" /></Svg>;
export const BellIcon = (p: P) => <Svg {...p}><path d="M6 8a6 6 0 0112 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.9 1.9 0 003.4 0" /></Svg>;
export const UserIcon = (p: P) => <Svg {...p}><circle cx="12" cy="8" r="4" /><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" /></Svg>;
export const PlusIcon = (p: P) => <Svg {...p}><path d="M12 5v14M5 12h14" /></Svg>;
export const LockIcon = (p: P) => <Svg {...p}><rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V8a4 4 0 018 0v3" /></Svg>;
export const CheckIcon = (p: P) => <Svg {...p}><path d="M5 12l5 5 9-10" /></Svg>;
export const BackIcon = (p: P) => <Svg {...p}><path d="M15 5l-7 7 7 7" /></Svg>;
export const FlagIcon = (p: P) => <Svg {...p}><path d="M5 21V4h11l-1.5 4L16 12H5" /></Svg>;
export const SendIcon = (p: P) => <Svg {...p}><path d="M4 12l16-8-6 16-2-7z" /></Svg>;
export const MailIcon = (p: P) => <Svg {...p}><rect x="3" y="5" width="18" height="14" rx="2" /><path d="M3 7l9 6 9-6" /></Svg>;
export const ShieldIcon = (p: P) => <Svg {...p}><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" /></Svg>;
export const CloseIcon = (p: P) => <Svg {...p}><path d="M6 6l12 12M18 6L6 18" /></Svg>;
export const ImageIcon = (p: P) => <Svg {...p}><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="9" cy="10" r="2" /><path d="M21 16l-5-5-9 9" /></Svg>;

export function Diamond({ size = 16, className = "" }: P) {
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" className={className}>
      <path d="M6 3h12l4 6-10 12L2 9z" fill="#F59E0B" stroke="#B45309" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}
