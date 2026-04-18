package genericsWildcardsClazzMethodParamUpperBoundsAdd;

import java.util.ArrayList;

import testing_lib.genericsWildcardsClazzMethodParamUpperBoundsAdd.GenericsWildcardsClazzMethodParamUpperBoundsAdd;

public class Main extends GenericsWildcardsClazzMethodParamUpperBoundsAdd {

	public static void main(String[] args) {
		GenericsWildcardsClazzMethodParamUpperBoundsAdd constr = new GenericsWildcardsClazzMethodParamUpperBoundsAdd();
		ArrayList<String> param1 = new ArrayList<String>();
		constr.method1(param1);
	}

	@Override
	public void method1(ArrayList<?> param1) {

	}
}
