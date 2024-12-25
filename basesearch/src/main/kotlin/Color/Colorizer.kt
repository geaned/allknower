package color

private const val ESCAPE = "\u001B"
private const val FG_JUMP = 10

enum class Color(baseCode: Int) {
    BLACK(30),
    RED(31),
    GREEN(32),
    YELLOW(33),
    BLUE(34),
    MAGENTA(35),
    CYAN(36),
    LIGHT_GRAY(37),

    DARK_GRAY(90),
    LIGHT_RED(91),
    LIGHT_GREEN(92),
    LIGHT_YELLOW(93),
    LIGHT_BLUE(94),
    LIGHT_MAGENTA(95),
    LIGHT_CYAN(96),
    WHITE(97);

    val foreground: String = "$ESCAPE[${baseCode + FG_JUMP}m"

    val background: String = "$ESCAPE[${baseCode}m"
}

class PrintColorizer {
    private val RESET = "$ESCAPE[0m"

    fun Colorize(stringToPrint: String, color: Color): String {
        return color.background + stringToPrint + RESET
    }

    fun ColorizeForeground(stringToPrint: String, color: Color): String {
        return color.foreground + stringToPrint + RESET
    }
}