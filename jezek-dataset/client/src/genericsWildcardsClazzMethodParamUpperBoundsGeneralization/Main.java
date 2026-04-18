package genericsWildcardsClazzMethodParamUpperBoundsGeneralization;

import java.util.ArrayList;

import testing_lib.genericsWildcardsClazzMethodParamUpperBoundsGeneralization.GenericsWildcardsClazzMethodParamUpperBoundsGeneralization;

public class Main extends GenericsWildcardsClazzMethodParamUpperBoundsGeneralization {

	public static void main(String[] args) {
		GenericsWildcardsClazzMethodParamUpperBoundsGeneralization constr = new GenericsWildcardsClazzMethodParamUpperBoundsGeneralization();
		ArrayList<Integer> param1 = new ArrayList<Integer>();
		constr.method1(param1);
	}

	@Override
	public void method1(ArrayList<? extends Integer> param1) {

	}
}
