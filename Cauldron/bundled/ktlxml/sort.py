import version
version.append ('$Revision: 81810 $')
del version


def stringAsNumber (number1, number2):

    if number1 == number2:
        return 0

    # It's possible that this function will get called with 'None'
    # as an argument. Casually patch over this possibility while
    # whistling and looking the other way. If a 'None' value is
    # present, consider that a trump card, in that None is the
    # smallest value possible.

    if number1 == 'None':
        return -1

    if number2 == 'None':
        return 1

    # Prefer ints, but accept floats as well.

    try:
        number1 = int (number1)
    except ValueError:
        number1 = float (number1)
    try:
        number2 = int (number2)
    except ValueError:
        number2 = float (number2)

    if number1 > number2:
        return 1

    if number1 < number2:
        return -1

    # The first equality check may not necessarily catch all
    # equalities. If we made it this far, though, equality
    # is fairly-well assured.

    return 0

