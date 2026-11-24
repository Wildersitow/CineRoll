import {
  ArrowDownIcon, ArrowLeftIcon, ArrowSquareOutIcon, CalendarBlankIcon, CurrencyCircleDollarIcon,
  CaretDownIcon, CaretLeftIcon, ChatCircleDotsIcon, GearSixIcon, GlobeIcon, ListBulletsIcon, MapTrifoldIcon, NavigationArrowIcon, PlayIcon, SignOutIcon, CaretRightIcon, ClockIcon, FilmStripIcon, HouseIcon,
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
}

export default function CinemaIcon({ name, weight = 'regular' }) {
  const Icon = icons[name]
  return <Icon aria-hidden="true" weight={weight} />
}
