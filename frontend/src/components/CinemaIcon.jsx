import {
  ArrowDownIcon, ArrowLeftIcon, ArrowSquareOutIcon, CalendarBlankIcon,
  CaretLeftIcon, CaretRightIcon, ClockIcon, FilmStripIcon, HouseIcon,
  MagnifyingGlassIcon, MapPinIcon, PencilSimpleIcon, ShareNetworkIcon,
  SparkleIcon, TelevisionIcon, TicketIcon, UserIcon, WarningCircleIcon,
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
}

export default function CinemaIcon({ name, weight = 'regular' }) {
  const Icon = icons[name]
  return <Icon aria-hidden="true" weight={weight} />
}
