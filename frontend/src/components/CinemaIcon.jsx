import {
  ArrowDownIcon, ArrowLeftIcon, ArrowUpIcon, AtIcon, EnvelopeSimpleIcon, EyeIcon, EyeSlashIcon, IdentificationCardIcon, LockSimpleIcon, PaperPlaneRightIcon, ArrowSquareOutIcon, CalendarBlankIcon, CurrencyCircleDollarIcon,
  CaretDownIcon, CaretLeftIcon, ChatCircleDotsIcon, GearSixIcon, GlobeIcon, KeyIcon, ListBulletsIcon, MapTrifoldIcon, NavigationArrowIcon, PlayIcon, SignOutIcon, CaretRightIcon, ClockIcon, FilmStripIcon, HouseIcon,
  MagnifyingGlassIcon, MapPinIcon, PencilSimpleIcon, ShareNetworkIcon,
  SparkleIcon, TelevisionIcon, TicketIcon, UserIcon, UsersIcon, WarningCircleIcon,
} from '@phosphor-icons/react'

const icons = {
  film: FilmStripIcon,
  home: HouseIcon,
  screen: TelevisionIcon,
  spark: SparkleIcon,
  clock: ClockIcon,
  pin: MapPinIcon,
  user: UserIcon,
  search: MagnifyingGlassIcon,
  left: CaretLeftIcon,
  right: CaretRightIcon,
  down: ArrowDownIcon,
  back: ArrowLeftIcon,
  external: ArrowSquareOutIcon,
  calendar: CalendarBlankIcon,
  ticket: TicketIcon,
  warning: WarningCircleIcon,
  edit: PencilSimpleIcon,
  share: ShareNetworkIcon,
  caretDown: CaretDownIcon,
  chat: ChatCircleDotsIcon,
  settings: GearSixIcon,
  signOut: SignOutIcon,
  play: PlayIcon,
  map: MapTrifoldIcon,
  directions: NavigationArrowIcon,
  globe: GlobeIcon,
  price: CurrencyCircleDollarIcon,
  list: ListBulletsIcon,
  users: UsersIcon,
  key: KeyIcon,
  up: ArrowUpIcon,
  at: AtIcon,
  mail: EnvelopeSimpleIcon,
  eye: EyeIcon,
  eyeOff: EyeSlashIcon,
  name: IdentificationCardIcon,
  lock: LockSimpleIcon,
  send: PaperPlaneRightIcon,
}

export default function CinemaIcon({ name, weight = 'regular' }) {
  const Icon = icons[name]
  return <Icon aria-hidden="true" weight={weight} />
}
